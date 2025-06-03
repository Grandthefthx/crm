import asyncio
import time
import logging
from telegram import InputMediaPhoto
from telegram.error import RetryAfter, TelegramError
from django.conf import settings
from tg_bots.bot_private.send import bot

logger = logging.getLogger('broadcast')

async def _send_async(bot_instance, user_id, text, markup=None, photo_paths=None, text_after_media=None):
    if photo_paths:
        if len(photo_paths) == 1:
            with open(photo_paths[0], 'rb') as f:
                await bot_instance.send_photo(
                    chat_id=user_id,
                    photo=f.read(),
                    caption=text,
                    reply_markup=markup,
                    parse_mode='HTML'
                )
        else:
            media = []
            for i, path in enumerate(photo_paths):
                with open(path, 'rb') as f:
                    content = f.read()
                    media.append(InputMediaPhoto(content, caption=text, parse_mode='HTML') if i == 0 else InputMediaPhoto(content))
            await bot_instance.send_media_group(chat_id=user_id, media=media)
            await bot_instance.send_message(chat_id=user_id, text=text_after_media or "\u200B", reply_markup=markup)
    else:
        await bot_instance.send_message(chat_id=user_id, text=text, reply_markup=markup, parse_mode='HTML')

def safe_send_message(chat_id, text, markup=None, photo_paths=None, text_after_media=None):
    while True:
        try:
            asyncio.run(_send_async(bot, chat_id, text, markup, photo_paths, text_after_media))
            return
        except RetryAfter as e:
            logger.warning(f"Rate limited. Sleeping for {e.retry_after} seconds")
            time.sleep(e.retry_after + 1)
        except TelegramError as e:
            logger.error(f"TelegramError: {e}")
            return
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return