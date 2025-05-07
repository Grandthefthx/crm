from django import forms
from .models import BroadcastMessage, TelegramClient

class BroadcastMessageForm(forms.ModelForm):
    class Meta:
        model = BroadcastMessage
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Фильтр по bot_source
        self.fields["recipients"].queryset = TelegramClient.objects.order_by("bot_source")
        self.fields["recipients"].help_text = "Фильтруй по источнику, например: private / public"
