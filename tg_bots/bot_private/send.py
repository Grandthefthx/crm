import asyncio
import logging
from telegram import Bot
from django.conf import settings

logger = logging.getLogger(__name__)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN_PRIVATE)

def send_broadcast_message(broadcast):
    from asgiref.sync import async_to_sync
    return async_to_sync(_send_broadcast)(broadcast)

async def _send_broadcast(broadcast):
    count = 0
    videos = list(broadcast.videos.all())
    for client in broadcast.recipients.all():
        try:
            for video in videos:
                with open(video.file.path, "rb") as f:
                    await bot.send_video(chat_id=client.user_id, video=f)
                    await asyncio.sleep(1)
            await bot.send_message(chat_id=client.user_id, text=broadcast.text)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при отправке {client.user_id}: {e}")
    return count
