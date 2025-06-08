import os
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from asgiref.sync import sync_to_async

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputFile,
    Message,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from core.models import TelegramClient, ClientAction, SupportMessage, PaymentUpload, BroadcastMessage
from tg_bots.bot_private.handlers.handler_vote import handle_vote_callback
from django.core.files.base import ContentFile

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEXT_DIR = BASE_DIR / "tg_bots" / "bot_private" / "texts"
REVIEW_MEDIA_DIR = BASE_DIR / "tg_bots" / "bot_private" / "media"
ABOUT_MEDIA_DIR = BASE_DIR / "tg_bots" / "bot_private" / "media" / "about"
TRANSFORM_FEEDBACK_MEDIA_DIR = BASE_DIR / "tg_bots" / "bot_private" / "media" / "transform_feedback"
UPLOADS_ROOT = BASE_DIR / "media" / "uploads"

log_path = BASE_DIR / "logs" / "bot.log"
logging.basicConfig(
    handlers=[logging.FileHandler(log_path)],
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
load_dotenv()

def load_text(name: str) -> str:
    try:
        return (TEXT_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return f"[текст '{name}' не найден]"

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Подробнее о канале 🐇", callback_data="about")],
        [InlineKeyboardButton("Оплатить участие 🌻", callback_data="payment")],
        [InlineKeyboardButton("Получить послание 💌", callback_data="get_message")],
        [InlineKeyboardButton("В открытый канал ✨", url="https://t.me/soul_evolucion")],
        [InlineKeyboardButton("Интенсив 🔥Трансформация энергии 🔥", callback_data="transform")],
        [InlineKeyboardButton("Задать вопрос ❔", callback_data="support")],
    ])

def transform_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Узнать подробнее 🐇", callback_data="transform_detail")],
        [InlineKeyboardButton("Участвовать 🔥", callback_data="transform_go")],
        [InlineKeyboardButton("⬅️ На главную", callback_data="main")],
    ])

def transform_go_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Получить реквизиты", url="https://t.me/soul_evolucion_care")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="transform")],
    ])

def about_menu(include_reviews: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if include_reviews:
        buttons.append([InlineKeyboardButton("Обратная связь 🌟", callback_data="reviews")])
    buttons.append([InlineKeyboardButton("Оплатить участие 🌻", callback_data="payment")])
    buttons.append([InlineKeyboardButton("⬅️ На главную", callback_data="main")])
    return InlineKeyboardMarkup(buttons)

def payment_menu(exclude: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = []
    if exclude != "pay_tg":
        buttons.append([InlineKeyboardButton("Tribute", callback_data="pay_tg")])
    if exclude != "pay_card_ru":
        buttons.append([InlineKeyboardButton("Карта РФ", callback_data="pay_card_ru")])
    buttons.append([InlineKeyboardButton("⬅️ На главную", callback_data="main")])
    return InlineKeyboardMarkup(buttons)

def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ На главную", callback_data="main")]])

@sync_to_async
def get_client(user_id):
    return TelegramClient.objects.filter(user_id=user_id).first()

@sync_to_async
def create_client_action(client, action):
    return ClientAction.objects.create(client=client, action=action)

@sync_to_async
def create_support_message(client, message):
    return SupportMessage.objects.create(client=client, message=message)

@sync_to_async
def create_payment_upload(client, f, filename):
    return PaymentUpload.objects.create(
        client=client,
        file=ContentFile(f.read(), name=f"uploads/{client.user_id}/{filename}"),
    )

@sync_to_async
def get_main_broadcast():
    return BroadcastMessage.objects.filter(comment="Послание для меню").first()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(load_text("main"), reply_markup=main_menu(), parse_mode="HTML")
    await sync_to_async(TelegramClient.objects.get_or_create)(user_id=user.id, defaults={
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "bot_source": "private",
    })
    client = await get_client(user.id)
    if client:
        await create_client_action(client, "start_private")

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    client = await get_client(user.id)
    if client:
        await create_client_action(client, f"clicked_{data}")

    if data == "about":
        media = []
        for i in range(1, 8):
            path = ABOUT_MEDIA_DIR / f"about{i}.jpg"
            if path.exists():
                with open(path, "rb") as f:
                    media.append(InputMediaPhoto(f.read()))
        if media:
            await context.bot.send_media_group(chat_id=query.message.chat_id, media=media)
        await query.message.reply_text(load_text("about"), reply_markup=about_menu(), parse_mode="HTML")
    elif data == "payment":
        await query.message.reply_text(load_text("payment"), reply_markup=payment_menu(), parse_mode="HTML")
    elif data == "support":
        await query.message.reply_text(load_text("support"), reply_markup=back_to_main(), parse_mode="HTML")
    elif data == "reviews":
        media = []
        for i in range(1, 9):
            path = REVIEW_MEDIA_DIR / f"re{i}.jpg"
            if path.exists():
                with open(path, "rb") as f:
                    media.append(InputMediaPhoto(f.read()))
        if media:
            await context.bot.send_media_group(chat_id=query.message.chat_id, media=media)
        await query.message.reply_text("🌟 Обратная связь подписчиков 🌟", reply_markup=about_menu(False), parse_mode="HTML")
    elif data == "pay_tg":
        await query.message.reply_text(load_text("payment_trib"), reply_markup=payment_menu("pay_tg"), parse_mode="HTML")
    elif data == "pay_card_ru":
        await query.message.reply_text(load_text("payment_card_ru"), reply_markup=payment_menu("pay_card_ru"), parse_mode="HTML")
    elif data == "main":
        await query.message.reply_text(load_text("main"), reply_markup=main_menu(), parse_mode="HTML")
    elif data == "transform":
        await query.message.reply_text(load_text("transform"), reply_markup=transform_menu(), parse_mode="HTML")
    elif data == "transform_detail":
        await query.message.reply_text(load_text("transform_detail"), reply_markup=transform_menu(), parse_mode="HTML")
    elif data == "transform_go":
        await query.message.reply_text(load_text("transform_go"), reply_markup=transform_go_menu(), parse_mode="HTML")
    elif data == "get_message":
        bm = await get_main_broadcast()
        if not bm:
            await query.message.reply_text("Послания сейчас нет.", reply_markup=main_menu(), parse_mode="HTML")
            return
        audios = list(await sync_to_async(lambda: list(bm.audios.all().order_by("choice_number")))())
        if not audios:
            await query.message.reply_text("Аудиофайлы для послания не найдены.", reply_markup=main_menu(), parse_mode="HTML")
            return
        buttons = [[
            InlineKeyboardButton(str(a.choice_number), callback_data=f"vote:{a.choice_number}:{bm.id}")
            for a in audios
        ]]
        await query.message.reply_text(
            "Выбери аудиопослание:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    txt = update.message.text.strip()
    client = await get_client(user.id)
    if client:
        await create_support_message(client, txt)
        await create_client_action(client, f"support_message: {txt}")
    await update.message.reply_text("✅ Вопрос получен. Мы свяжемся с вами в личных сообщениях.",
                                    reply_markup=main_menu(), parse_mode="HTML")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message: Message = update.message
    user = message.from_user
    if message.video:
        tg_file = await context.bot.get_file(message.video.file_id)
        is_video = True
    elif message.document:
        tg_file = await context.bot.get_file(message.document.file_id)
        is_video = message.document.mime_type.startswith("video") if message.document.mime_type else False
    else:
        tg_file = await context.bot.get_file(message.photo[-1].file_id)
        is_video = False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original = tg_file.file_path.split("/")[-1]
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", original)
    filename = f"{timestamp}_{sanitized}"

    user_dir = UPLOADS_ROOT / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    filepath = user_dir / filename
    await tg_file.download_to_drive(custom_path=str(filepath))

    client = await get_client(user.id)
    if client:
        if not is_video:
            with open(filepath, "rb") as f:
                await create_payment_upload(client, f, filename)
        await create_client_action(client, f"uploaded_payment: {filename}")

    await update.message.reply_text("✅ Чек получен. Проверим и добавим в канал.", parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Ошибка: %s", context.error, exc_info=True)
    if hasattr(update, "effective_message") and update.effective_message:
        await update.effective_message.reply_text("⚠️ Произошла ошибка. Попробуйте снова.")

def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN_PRIVATE")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_vote_callback, pattern=r"^vote:"))
    app.add_handler(CallbackQueryHandler(handle_main_menu, pattern=r"^(about|payment|support|reviews|pay_tg|pay_card_ru|main|get_message|transform|transform_detail|transform_go)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.Document.IMAGE
            | filters.VIDEO
            | filters.Document.VIDEO,
            handle_media,
        )
    )
    app.add_error_handler(error_handler)
    logger.info("Бот запущен (async)")
    app.run_polling()

if __name__ == "__main__":
    main()
