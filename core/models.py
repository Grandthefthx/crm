
from django.db import models

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

    def __str__(self):
        return self.username or str(self.user_id)


class ClientAction(models.Model):
    client = models.ForeignKey(TelegramClient, on_delete=models.CASCADE, related_name='actions')
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

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
    comment = models.CharField("Комментарий", max_length=255, default="Без названия")
    recipients = models.ManyToManyField(TelegramClient, verbose_name="Получатели")
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"

    def __str__(self):
        return f"Рассылка #{self.id} — {self.created_at.strftime('%d.%m.%Y %H:%M')}"


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
