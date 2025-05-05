from django.contrib import admin  # ← ЭТО ОБЯЗАТЕЛЬНО
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
import time
import asyncio  # ← Вот эта строка обязательна

from .models import TelegramClient, ClientAction, SupportMessage, BroadcastMessage, BroadcastDelivery

class BroadcastDeliveryInline(admin.TabularInline):
    model = BroadcastDelivery
    extra = 0
    readonly_fields = ("recipient", "sent_at", "status", "error_message")
    can_delete = False

@admin.register(TelegramClient)
class TelegramClientAdmin(admin.ModelAdmin):
    list_display = ("user_id", "username", "first_name", "created_at", "bot_source")
    search_fields = ("username", "first_name", "last_name")
    list_filter = ("bot_source",)
    inlines = [BroadcastDeliveryInline]

@admin.register(ClientAction)
class ClientActionAdmin(admin.ModelAdmin):
    list_display = ("client", "action", "timestamp")
    list_filter = ("action",)
    search_fields = ("client__username", "action")

@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("client", "message", "timestamp")
    search_fields = ("client__username", "message")
    list_filter = ("timestamp",)

@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "short_text", "created_at", "sent", "send_button")

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
    send_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("send/<int:pk>", self.admin_site.admin_view(self.send_broadcast), name="send_broadcast"),
        ]
        return custom + urls

    def send_broadcast(self, request, pk):
        from django.conf import settings
        from telegram import Bot

        msg = BroadcastMessage.objects.get(pk=pk)
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN_PRIVATE)

        success, fail = 0, 0

        for user in msg.recipients.all():
            if not user.user_id:
                print(f"⚠️ Пропущен: нет user_id у {user}")
                BroadcastDelivery.objects.create(
                    message=msg,
                    recipient=user,
                    status='failed',
                    error_message='Нет user_id'
                )
                fail += 1
                continue

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.send_message(chat_id=user.user_id, text=msg.text))
                loop.close()
                time.sleep(0.3)

                BroadcastDelivery.objects.create(
                    message=msg,
                    recipient=user,
                    status='sent'
                )
                success += 1
            except Exception as e:
                BroadcastDelivery.objects.create(
                    message=msg,
                    recipient=user,
                    status='failed',
                    error_message=str(e)
                )
                print(f"❌ Ошибка для {user.user_id}: {e}")
                fail += 1

        msg.sent = True
        msg.save()

        messages.success(
            request,
            f"✅ Отправлено: {success}, ошибок: {fail}"
        )
        return redirect("..")