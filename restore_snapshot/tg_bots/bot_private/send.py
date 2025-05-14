import asyncio
from telegram import Bot
from django.conf import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN_PRIVATE)

def send_broadcast_message(broadcast):
    from asgiref.sync import async_to_sync
    return async_to_sync(_send_broadcast)(broadcast)

async def _send_broadcast(broadcast):
    count = 0
    for client in broadcast.recipients.all():
        try:
            await bot.send_message(chat_id=client.user_id, text=broadcast.text)
            count += 1
        except Exception as e:
            print(f"Ошибка при отправке {client.user_id}: {e}")
    return count
