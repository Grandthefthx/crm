import os
import logging
from celery import Celery

# Установка переменной окружения Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

logger = logging.getLogger(__name__)

app = Celery("crm")

# Чтение конфигурации из settings.py (с префиксом CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматическое обнаружение задач в приложениях
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    logger.info(f"Request: {self.request!r}")
