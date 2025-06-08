import json
import logging
import time
import asyncio
import os

from celery import shared_task
from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest
from core.models import BroadcastMessage, BroadcastDelivery, BroadcastAudio, BroadcastVideo
from pydub import AudioSegment

logger = logging.getLogger("broadcast")

def build_keyboard(raw):
    if not raw:
        return None
    try:
        data = json.loads(raw)
        keyboard = [
            [
                InlineKeyboardButton(
                    text=b["text"],
                    url=b.get("url"),
                    callback_data=b.get("callback_data")
                ) for b in row
            ] for row in data
        ]
        return InlineKeyboardMarkup(keyboard)
    except Exception:
        logger.exception("Не удалось распарсить buttons_json")
        return None

def _sync_send(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    else:
        return loop.run_until_complete(coro)

@shared_task(bind=True, name="core.tasks.send_broadcast")
def send_broadcast(self, broadcast_id: int):
    tid = self.request.id
    logger.info("🚀 Старт рассылки id=%s (task %s)", broadcast_id, tid)

    try:
        bm = BroadcastMessage.objects.get(pk=broadcast_id)
    except BroadcastMessage.DoesNotExist:
        logger.error("❌ BroadcastMessage %s не найден", broadcast_id)
        return

    keyboard = build_keyboard(bm.buttons_json)
    ok = failed = 0
    for client in bm.recipients.all():
        delivery, _ = BroadcastDelivery.objects.update_or_create(
            message=bm,
            recipient=client,
            defaults={"status": "pending", "error_message": ""},
        )
        try:
            bot = Bot(
                token=settings.TELEGRAM_BOT_TOKEN_PRIVATE,
                request=HTTPXRequest(connect_timeout=10, read_timeout=30),
            )

            for video in bm.videos.all():
                with open(video.file.path, "rb") as f:
                    _sync_send(
                        bot.send_video(chat_id=client.user_id, video=f)
                    )
                    time.sleep(1)

            coro = bot.send_message(
                chat_id=client.user_id,
                text=bm.text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            msg = _sync_send(coro)
            logger.info("📨 Ответ Telegram: %s", msg.to_dict())
            delivery.status = "sent"
            # delivery.message_id = msg.message_id    # <-- ЭТУ СТРОКУ НЕ НУЖНО!
            delivery.save()
            logger.info("✅ Успешно отправлено пользователю %s", client.user_id)
            ok += 1
        except Exception as exc:
            logger.exception("⚠️ Ошибка при отправке пользователю %s", client.user_id)
            delivery.status = "failed"
            delivery.error_message = str(exc)[:500]
            delivery.save()
            failed += 1
        time.sleep(1)

    bm.sent = True
    bm.save(update_fields=["sent"])

    logger.info(
        "📬 Рассылка %s завершена: ok=%d, failed=%d (task %s)",
        broadcast_id,
        ok,
        failed,
        tid,
    )

@shared_task(name="core.tasks.convert_audio_to_mp3")
def convert_audio_to_mp3_task(audio_id: int):
    try:
        audio = BroadcastAudio.objects.get(id=audio_id)
        ogg_path = audio.file.path
        mp3_path = ogg_path.replace(".ogg", ".mp3")

        AudioSegment.from_file(ogg_path).export(mp3_path, format="mp3")

        with open(mp3_path, "rb") as f:
            audio.mp3_file.save(os.path.basename(mp3_path), f, save=True)

        logger.info("✅ Успешная конвертация .ogg → .mp3 (%s)", mp3_path)

    except BroadcastAudio.DoesNotExist:
        logger.exception("❌ BroadcastAudio не найден при конвертации .ogg → .mp3")
    except Exception as e:
        logger.exception("❌ Ошибка при конвертации .ogg → .mp3: %s", str(e))
