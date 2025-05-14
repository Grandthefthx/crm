import asyncio
import csv
import logging
import time
import traceback
import json
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from .forms import BroadcastMessageForm
from .models import (
    TelegramClient,
    ClientAction,
    SupportMessage,
    BroadcastMessage,
    BroadcastDelivery,
    PaymentUpload,
)

logger = logging.getLogger("broadcast")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("broadcast.log")
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)


class BroadcastDeliveryInline(admin.TabularInline):
    model = BroadcastDelivery
    extra = 0
    readonly_fields = ("recipient", "status", "sent_at", "error_message")
    can_delete = False
    show_change_link = True


@admin.register(TelegramClient)
class TelegramClientAdmin(admin.ModelAdmin):
    list_display = ("user_id", "username", "first_name", "created_at", "bot_source")
    search_fields = ("username", "first_name", "last_name")
    list_filter = ("bot_source", "created_at")
    inlines = [BroadcastDeliveryInline]
    ordering = ("-created_at",)


@admin.register(ClientAction)
class ClientActionAdmin(admin.ModelAdmin):
    list_display = ("client", "action", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("client__username", "action")
    ordering = ("-timestamp",)


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("client", "message", "timestamp")
    search_fields = ("client__username", "message")
    list_filter = ("timestamp",)
    ordering = ("-timestamp",)


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    form = BroadcastMessageForm
    list_display = ("id", "short_text", "comment", "created_at", "sent", "send_button")
    search_fields = ("text", "comment")
    list_filter = ("sent", "created_at")
    ordering = ("-created_at",)
    actions = ["export_csv"]
    inlines = [BroadcastDeliveryInline]

    def short_text(self, obj):
        return obj.text[:40] + "..." if len(obj.text) > 40 else obj.text
    short_text.short_description = "Текст"

    def send_button(self, obj):
        if not obj.sent:
            return format_html(
                '<a class="button" href="{}">Отправить сейчас</a>',
                f"send/{obj.pk}"
            )
        return "Отправлено"
    send_button.short_description = "Действие"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("send/<int:pk>", self.admin_site.admin_view(self.send_broadcast), name="send_broadcast"),
        ]
        return custom + urls

    def run_async(self, coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.ensure_future(coro)
            return loop.run_until_complete(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)

    def send_broadcast(self, request, pk):
        from django.conf import settings
        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.error import TelegramError, NetworkError

        msg = BroadcastMessage.objects.get(pk=pk)
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN_PRIVATE)

        success, fail = 0, 0
        reply_markup = None

        if msg.buttons_json:
            try:
                keyboard_data = json.loads(msg.buttons_json)
                keyboard = [
                    [InlineKeyboardButton(**btn) for btn in row]
                    for row in keyboard_data
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            except Exception as e:
                messages.error(request, f"❌ Ошибка кнопок: {e}")
                return redirect(reverse("admin:core_broadcastmessage_changelist"))

        async def send_telegram_message(bot_instance, user_id, text, markup):
            await bot_instance.send_message(chat_id=user_id, text=text, reply_markup=markup, parse_mode='HTML')

        for user in msg.recipients.all():
            if not user.user_id:
                BroadcastDelivery.objects.update_or_create(
                    message=msg,
                    recipient=user,
                    defaults={'status': 'failed', 'error_message': 'Нет user_id'}
                )
                fail += 1
                continue

            try:
                self.run_async(send_telegram_message(bot, user.user_id, msg.text, reply_markup))

                BroadcastDelivery.objects.update_or_create(
                    message=msg,
                    recipient=user,
                    defaults={'status': 'sent', 'error_message': ''}
                )

                success += 1
                time.sleep(0.3)

            except (NetworkError, TelegramError) as e:
                error_msg = f"Telegram API error: {str(e)}"
                BroadcastDelivery.objects.update_or_create(
                    message=msg,
                    recipient=user,
                    defaults={'status': 'failed', 'error_message': error_msg}
                )
                fail += 1

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                traceback.print_exc()
                BroadcastDelivery.objects.update_or_create(
                    message=msg,
                    recipient=user,
                    defaults={'status': 'failed', 'error_message': error_msg}
                )
                fail += 1

        msg.sent = True
        msg.save()

        messages.success(
            request,
            f"✅ Broadcast завершён: успешно — {success}, с ошибкой — {fail}"
        )
        return redirect(reverse("admin:core_broadcastmessage_changelist"))

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="broadcasts.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Comment", "Text", "Created At", "Sent"])

        for obj in queryset:
            writer.writerow([obj.id, obj.comment, obj.text, obj.created_at, obj.sent])

        return response
    export_csv.short_description = "📤 Экспортировать в CSV"
