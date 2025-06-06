from telegram import Update, InputFile
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
import logging
import os

from core.models import TelegramClient, BroadcastMessage, BroadcastVote, BroadcastAudio

logger = logging.getLogger(__name__)

@sync_to_async
def get_vote_info(user_id, vote_key):
    parts = vote_key.split(":")
    if len(parts) != 3 or parts[0] != "vote":
        return None, None, None, "⚠️ Неверный формат callback."

    try:
        choice = int(parts[1])
        broadcast_id = int(parts[2])
    except ValueError:
        return None, None, None, "⚠️ Ошибка разбора номера."

    client = TelegramClient.objects.filter(user_id=user_id).first()
    if not client:
        return None, None, None, "⚠️ Клиент не найден."

    broadcast = BroadcastMessage.objects.filter(id=broadcast_id).first()
    if not broadcast:
        return None, None, None, "⚠️ Рассылка не найдена."

    already = BroadcastVote.objects.filter(message=broadcast, client=client).exists()
    if already:
        return None, None, None, "Вы уже получили послание 🙅"

    audio = BroadcastAudio.objects.filter(message=broadcast, choice_number=choice).first()
    return client, broadcast, audio, None

@sync_to_async
def save_vote(client, broadcast, choice, audio):
    BroadcastVote.objects.create(
        client=client,
        message=broadcast,
        choice_number=choice,
        voice_file=audio.file if audio else None
    )

async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    vote_key = query.data
    logger.info(f"[VOTE DEBUG] callback_data={vote_key}, user_id={user_id}")

    client, broadcast, audio, error = await get_vote_info(user_id, vote_key)

    if error:
        logger.warning(f"Ошибка голосования от user {user_id}: {error}")
        try:
            await query.delete_message()
        except Exception:
            pass
        await context.bot.send_message(chat_id=query.message.chat_id, text=error)
        return

    await save_vote(client, broadcast, int(vote_key.split(":")[1]), audio)

    # Удаляем исходное сообщение с кнопками
    try:
        await query.delete_message()
    except Exception:
        pass

    mp3_path = None
    if audio and audio.mp3_file and audio.mp3_file.name:
        try:
            mp3_path = audio.mp3_file.path
        except ValueError:
            mp3_path = None
    if audio and audio.mp3_file:
        # >>> Главное отличие здесь <<<
        # Используется только то имя, что указано в custom_filename (даже без .mp3), если оно есть.
        if audio.custom_filename:
            filename = audio.custom_filename
        elif mp3_path:
            filename = os.path.basename(mp3_path)
        else:
            filename = None
        exists_flag = os.path.exists(mp3_path) if mp3_path else False
        logger.info(f"📎 Отправка mp3-аудио: {mp3_path}, exists={exists_flag}, filename={filename}")
        if mp3_path and os.path.exists(mp3_path):
            with open(mp3_path, "rb") as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=InputFile(f, filename=filename),
                    caption=audio.caption or "✅ Ваш голос учтён. Спасибо!",
                    parse_mode="HTML"
                )
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="⚠️ mp3-файл не найден.")
    else:
        await context.bot.send_message(chat_id=query.message.chat_id, text="✅ Голос принят, но аудио не найдено.")
