from django.db import models
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import json
import os
from django.conf import settings
from pydub import AudioSegment
from django.db import transaction


def upload_to_payment(instance, filename):
    return f"uploads/{instance.client.user_id}/{filename}"


class TelegramClient(models.Model):
    user_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    bot_source = models.CharField(max_length=50, null=True, blank=True)
    awaiting_support = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокировал бота")

    class Meta:
        verbose_name = "Клиент Telegram"
        verbose_name_plural = "Клиенты Telegram"

    def __str__(self):
        return self.username or str(self.user_id)


class ClientAction(models.Model):
    client = models.ForeignKey(TelegramClient, on_delete=models.CASCADE, related_name='actions')
    action = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Действие клиента"
        verbose_name_plural = "Действия клиентов"

    def __str__(self):
        return f"{self.client.username or self.client.user_id}: {self.action} at {self.timestamp}"


class SupportMessage(models.Model):
    client = models.ForeignKey(TelegramClient, on_delete=models.CASCADE, related_name='support_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self):
        return f"{self.client.username or self.client.user_id}: {self.message[:30]}"


class BroadcastMessage(models.Model):
    text = models.TextField("Текст сообщения")
    text_after_media = models.TextField("Текст после фото (если их много)", blank=True, null=True)
    comment = models.CharField("Комментарий", max_length=255, default="Без названия")
    recipients = models.ManyToManyField(TelegramClient, verbose_name="Получатели")
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    buttons_json = models.TextField("Кнопки (JSON)", blank=True, null=True)
    photo = models.ImageField(upload_to="broadcasts/", blank=True, null=True, verbose_name="Фото")

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"

    def __str__(self):
        if self.created_at:
            date_str = self.created_at.strftime('%d.%m.%Y %H:%M')
        else:
            date_str = "без даты"
        return f"Рассылка #{self.id} — {date_str}"

    def get_reply_markup(self):
        if not self.buttons_json:
            return None
        try:
            data = json.loads(self.buttons_json)
            keyboard = [[InlineKeyboardButton(**btn) for btn in row] for row in data]
            return InlineKeyboardMarkup(keyboard)
        except Exception:
            return None


class BroadcastPhoto(models.Model):
    message = models.ForeignKey(BroadcastMessage, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="broadcasts/photos/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Фото рассылки"
        verbose_name_plural = "Фото рассылки"

    def __str__(self):
        return f"Фото к рассылке #{self.message.id}"


class BroadcastVideo(models.Model):
    message = models.ForeignKey(BroadcastMessage, on_delete=models.CASCADE, related_name="videos")
    file = models.FileField(upload_to="broadcasts/videos/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Видео рассылки"
        verbose_name_plural = "Видео рассылки"

    def __str__(self):
        return f"Видео к рассылке #{self.message.id}"


class BroadcastDelivery(models.Model):
    message = models.ForeignKey(BroadcastMessage, on_delete=models.CASCADE, related_name='deliveries')
    recipient = models.ForeignKey(TelegramClient, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('sent', 'Отправлено'), ('failed', 'Ошибка')]
    )
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('message', 'recipient')
        verbose_name = "Доставка сообщения"
        verbose_name_plural = "Доставки сообщений"

    def __str__(self):
        return f"{self.recipient} ← {self.message} [{self.status}]"


class PaymentUpload(models.Model):
    client = models.ForeignKey(TelegramClient, on_delete=models.CASCADE)
    file = models.ImageField(upload_to=upload_to_payment, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Загруженный чек"
        verbose_name_plural = "Загруженные чеки"

    def __str__(self):
        return f"Чек от {self.client.username or self.client.user_id} — {self.uploaded_at.strftime('%d.%m.%Y %H:%M')}"


class BroadcastAudio(models.Model):
    message = models.ForeignKey(BroadcastMessage, on_delete=models.CASCADE, related_name="audios")
    choice_number = models.PositiveSmallIntegerField()
    file = models.FileField(upload_to='voice/')
    mp3_file = models.FileField(upload_to='voice_mp3/', blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    custom_filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Название файла для отправки в Telegram (с расширением .mp3)"
    )

    def __str__(self):
        return f"Audio {self.choice_number} for Broadcast #{self.message.id}"


class BroadcastVote(models.Model):
    message = models.ForeignKey(BroadcastMessage, on_delete=models.CASCADE, related_name="votes")
    client = models.ForeignKey(TelegramClient, on_delete=models.CASCADE)
    choice_number = models.PositiveSmallIntegerField()
    voice_file = models.FileField(upload_to='voice_responses/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'client')

    def __str__(self):
        return f"Vote: {self.client} chose {self.choice_number} for #{self.message.id}"


# async конвертация через celery
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=BroadcastAudio)
def handle_broadcastaudio_post_save(sender, instance, created, **kwargs):
    if created:
        from core.tasks import convert_audio_to_mp3_task  # ← ленивый импорт
        transaction.on_commit(lambda: convert_audio_to_mp3_task.delay(instance.id))
