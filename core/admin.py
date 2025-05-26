import asyncio
import csv
import json
import logging
import sys
import time
import traceback

from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from telegram import InputMediaPhoto

from .forms import BroadcastAttachForm, BroadcastMessageForm
from .models import (
    BroadcastDelivery,
    BroadcastMessage,
    BroadcastPhoto,
    BroadcastAudio,
    BroadcastVote,
    ClientAction,
    PaymentUpload,
    SupportMessage,
    TelegramClient,
)

logger = logging.getLogger("broadcast")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)
logger.info("✅ Логгер инициализирован в stdout")


class BroadcastDeliveryInline(admin.TabularInline):
    model = BroadcastDelivery
    extra = 0
    readonly_fields = ("recipient", "status", "sent_at", "error_message")
    can_delete = False
    show_change_link = True


class BroadcastPhotoInline(admin.TabularInline):
    model = BroadcastPhoto
    extra = 1
    fields = ("image", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class BroadcastAudioInline(admin.TabularInline):
    model = BroadcastAudio
    extra = 0
    fields = ("choice_number", "caption", "file", "custom_filename")


class BroadcastVoteInline(admin.TabularInline):
    model = BroadcastVote
    extra = 0
    readonly_fields = ("client", "choice_number", "voice_file", "created_at")
    can_delete = False


@admin.action(description="📨 Добавить в рассылку")
def attach_to_broadcast(modeladmin, request, queryset):
    if "apply" in request.POST:
        form = BroadcastAttachForm(request.POST)
        if form.is_valid():
            broadcast = form.cleaned_data["broadcast"]
            before = broadcast.recipients.count()
            broadcast.recipients.add(*queryset)
            added = broadcast.recipients.count() - before
            messages.success(request, f"✅ Добавлено {added} клиентов в рассылку.")
            return HttpResponseRedirect(request.get_full_path())
    else:
        form = BroadcastAttachForm()

    context = {
        "clients": queryset,
        "form": form,
        "title": "Выбери рассылку для добавления клиентов",
        "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
    }
    return TemplateResponse(request, "admin/attach_to_broadcast.html", context)


@admin.register(TelegramClient)
class TelegramClientAdmin(admin.ModelAdmin):
    actions = [attach_to_broadcast]
    list_display = (
        "user_id",
        "username",
        "first_name",
        "created_at",
        "bot_source",
        "is_blocked",
        "broadcast_count",
        "last_broadcasts",
    )
    search_fields = ("username", "first_name", "last_name", "user_id")
    list_filter = ("bot_source", "created_at", "is_blocked")
    inlines = [BroadcastDeliveryInline]
    ordering = ("-created_at",)

    def broadcast_count(self, obj):
        return obj.broadcastdelivery_set.count()

    broadcast_count.short_description = "Получено рассылок"

    def last_broadcasts(self, obj):
        deliveries = (
            obj.broadcastdelivery_set.select_related("message")
            .order_by("-sent_at")[:3]
        )
        if not deliveries:
            return "—"
        return format_html(
            "<br>".join(
                [
                    f'<a href="/admin/core/broadcastmessage/{d.message.id}/change/">#{d.message.id} — {d.message.comment}</a>'
                    for d in deliveries
                ]
            )
        )

    last_broadcasts.short_description = "Последние рассылки"
    last_broadcasts.allow_tags = True


@admin.register(ClientAction)
class ClientActionAdmin(admin.ModelAdmin):
    list_display = ("client", "action", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("client__username", "action")
    ordering = ("-timestamp",)


@admin.register(PaymentUpload)
class PaymentUploadAdmin(admin.ModelAdmin):
    list_display = ("client", "uploaded_at", "image_preview")
    search_fields = ("client__username",)
    list_filter = ("uploaded_at",)
    ordering = ("-uploaded_at",)

    def image_preview(self, obj):
        if obj.file:
            return format_html('<img src="{}" width="100" />', obj.file.url)
        return ""

    image_preview.short_description = "Превью"


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("client", "message", "timestamp")
    search_fields = ("client__username", "message")
    list_filter = ("timestamp",)
    ordering = ("-timestamp",)


from core.tasks import send_broadcast as send_broadcast_task


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    form = BroadcastMessageForm
    list_display = ("id", "short_text", "comment", "created_at", "sent", "send_button")
    search_fields = ("text", "comment")
    list_filter = ("sent", "created_at")
    ordering = ("-created_at",)
    actions = ["export_csv"]
    inlines = [
        BroadcastDeliveryInline,
        BroadcastPhotoInline,
        BroadcastAudioInline,
        BroadcastVoteInline,
    ]

    def short_text(self, obj):
        return obj.text[:40] + "..." if len(obj.text) > 40 else obj.text

    short_text.short_description = "Текст"

    def send_button(self, obj):
        if not obj.sent:
            return format_html(
                '<a class="button" href="{}">Отправить сейчас</a>',
                reverse("admin:send_broadcast", args=[obj.pk]),
            )
        return "Отправлено"

    send_button.short_description = "Действие"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "send/<int:pk>",
                self.admin_site.admin_view(self.send_broadcast),
                name="send_broadcast",
            ),
        ]
        return custom + urls

    def send_broadcast(self, request, pk):
        msg = BroadcastMessage.objects.get(pk=pk)
        send_broadcast_task.delay(pk)

        messages.success(
            request,
            f"🚀 Рассылка #{msg.id} поставлена в очередь Celery "
            f"({msg.recipients.count()} получателей)",
        )
        return redirect(reverse("admin:core_broadcastmessage_changelist"))

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

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="broadcasts.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Comment", "Text", "Created At", "Sent"])

        for obj in queryset:
            writer.writerow([obj.id, obj.comment, obj.text, obj.created_at, obj.sent])

        return response

    export_csv.short_description = "📤 Экспортировать в CSV"
