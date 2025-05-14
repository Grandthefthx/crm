import os
import sys
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Запускает приватного Telegram-бота"

    def handle(self, *args, **kwargs):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        os.environ.setdefault('TELEGRAM_BOT_TOKEN', os.environ['TELEGRAM_BOT_TOKEN_PRIVATE'])
        sys.path.append(os.getcwd())
        from tg_bots.bot_private.main import main
        main()
