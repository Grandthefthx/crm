from django import forms
from .models import BroadcastMessage, TelegramClient
import json
import logging

logger = logging.getLogger(__name__)

class BroadcastMessageForm(forms.ModelForm):
    button_texts = forms.CharField(
        label="Текст кнопок (через |||)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2})
    )
    button_urls = forms.CharField(
        label="URL или callback (через |||)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2})
    )
    button_types = forms.CharField(
        label="Тип кнопок (url или callback через |||)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2})
    )

    class Meta:
        model = BroadcastMessage
        fields = ["text", "comment", "recipients", "sent", "buttons_json"]
        widgets = {
            "buttons_json": forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["recipients"].queryset = TelegramClient.objects.order_by("bot_source")
        self.initial["button_texts"] = ""
        self.initial["button_urls"] = ""
        self.initial["button_types"] = ""

        if self.instance and self.instance.buttons_json:
            try:
                buttons = json.loads(self.instance.buttons_json)
                texts, urls, types = [], [], []
                for row in buttons:
                    for btn in row:
                        texts.append(btn.get("text", ""))
                        if "url" in btn:
                            urls.append(btn["url"])
                            types.append("url")
                        elif "callback_data" in btn:
                            urls.append(btn["callback_data"])
                            types.append("callback")
                self.initial["button_texts"] = "|||".join(texts)
                self.initial["button_urls"] = "|||".join(urls)
                self.initial["button_types"] = "|||".join(types)
            except Exception as e:
                logger.warning("⚠️ Ошибка парсинга buttons_json: %s", e)

    def clean(self):
        cleaned_data = super().clean()
        texts = cleaned_data.get("button_texts", "").split("|||")
        urls = cleaned_data.get("button_urls", "").split("|||")
        types = cleaned_data.get("button_types", "").split("|||")

        buttons = []
        row = []
        for t, u, tp in zip(texts, urls, types):
            t, u, tp = t.strip(), u.strip(), tp.strip().lower()
            if not t or not u or tp not in ("url", "callback"):
                continue
            if tp == "url":
                row.append({"text": t, "url": u})
            else:
                row.append({"text": t, "callback_data": u})

        if row:
            json_result = json.dumps([row])
            cleaned_data["buttons_json"] = json_result
            logger.info("✅ CLEANED buttons_json: %s", json_result)
        else:
            cleaned_data["buttons_json"] = ""
            logger.info("🟡 CLEANED buttons_json пуст")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.buttons_json = self.cleaned_data.get("buttons_json", "")
        logger.info("💾 SAVE buttons_json: %s", instance.buttons_json)
        if commit:
            instance.save()
            self.save_m2m()
        return instance
