import os
import sys
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Запускает Telegram-бота"

    def handle(self, *args, **kwargs):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        sys.path.append(os.getcwd())
        from tg_bots.bot_public.main import main
        main()
