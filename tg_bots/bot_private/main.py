from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    Message
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext
)
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import os
from pathlib import Path
from datetime import datetime
import re
from django.core.files import File
from telegram.error import Forbidden, RetryAfter, BadRequest, TelegramError
import asyncio

from core.models import TelegramClient, ClientAction, SupportMessage, PaymentUpload
from asgiref.sync import sync_to_async

# ───── Настройка логгера с ротацией ─────
BASE_DIR = Path(__file__).resolve().parent
log_path = BASE_DIR / "bot.log"

handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
logging.basicConfig(
    handlers=[handler],
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ───── Загрузка переменных ─────
load_dotenv()


async def send_message_safe(bot, chat_id, text, parse_mode='HTML', **kwargs):
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, **kwargs)
    except Forbidden:
        logger.warning(f"User {chat_id} blocked the bot.")
    except RetryAfter as e:
        wait_time = int(e.retry_after)
        logger.warning(f"Rate limit exceeded. Sleeping for {wait_time} sec.")
        await asyncio.sleep(wait_time)
        return await send_message_safe(bot, chat_id, text, parse_mode=parse_mode, **kwargs)
    except BadRequest as e:
        logger.error(f"Bad request: {e}")
    except TelegramError as e:
        logger.exception(f"Telegram error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")

@sync_to_async
def save_telegram_user(user):
    try:
        logger.info(f"Saving user {user.id}")
        TelegramClient.objects.get_or_create(
            user_id=user.id,
            defaults={
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'bot_source': 'private',
            }
        )
    except Exception as e:
        logger.exception(f"save_telegram_user error: {e}")

@sync_to_async
def log_action(user_id, action_name):
    try:
        client = TelegramClient.objects.filter(user_id=user_id).first()
        if client:
            ClientAction.objects.create(client=client, action=action_name)
    except Exception as e:
        logger.exception(f"log_action error: {e}")

@sync_to_async
def save_support_message(user_id, text):
    try:
        client = TelegramClient.objects.filter(user_id=user_id).first()
        if client:
            SupportMessage.objects.create(client=client, message=text)
    except Exception as e:
        logger.exception(f"save_support_message error: {e}")

@sync_to_async
def save_payment_upload(user_id, file: File):
    try:
        client = TelegramClient.objects.filter(user_id=user_id).first()
        if client:
            PaymentUpload.objects.create(client=client, file=file)
    except Exception as e:
        logger.exception(f"save_payment_upload error: {e}")


def load_text(name: str) -> str:
    path = BASE_DIR / "texts" / f"{name}.txt"
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return f"[текст '{name}' не найден]"


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Подробнее о канале 🐇", callback_data="about")],
        [InlineKeyboardButton("Оплатить участие 🎫", callback_data="payment")],
        [InlineKeyboardButton("Задать вопрос ❔", callback_data="support")]
    ])

def about_menu(include_reviews=True):
    buttons = []
    if include_reviews:
        buttons.append([InlineKeyboardButton("Обратная связь 🌟", callback_data="reviews")])
    buttons.append([InlineKeyboardButton("Оплатить участие 🎫", callback_data="payment")])
    buttons.append([InlineKeyboardButton("На главную ⬅️", callback_data="main")])
    return InlineKeyboardMarkup(buttons)

def payment_menu(exclude=None):
    buttons = []
    if exclude != "pay_tg":
        buttons.append([InlineKeyboardButton("Tribute", callback_data="pay_tg")])
    if exclude != "pay_card_ru":
        buttons.append([InlineKeyboardButton("Карта РФ", callback_data="pay_card_ru")])
    buttons.append([InlineKeyboardButton("На главную ⬅️", callback_data="main")])
    return InlineKeyboardMarkup(buttons)

def back_to_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("На главную ⬅️", callback_data="main")]
    ])


async def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    await save_telegram_user(user)
    await log_action(user.id, "start_private")
    await update.message.reply_text(
        load_text("main"),
        reply_markup=main_menu(),
        parse_mode='HTML'  # ✅
    )

async def handle_main_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    await log_action(user.id, f"clicked_{data}")

    if data == "about":
        await send_message_safe(context.bot, query.message.chat_id, load_text("about"), reply_markup=about_menu())
    elif data == "payment":
        await send_message_safe(context.bot, query.message.chat_id, load_text("payment"), reply_markup=payment_menu())
    elif data == "support":
        await send_message_safe(context.bot, query.message.chat_id, load_text("support"), reply_markup=back_to_main())
    elif data == "reviews":
        media_path = BASE_DIR / "media"
        media = []
        for i in range(1, 9):
            file_path = media_path / f"re{i}.jpg"
            if file_path.exists():
                media.append(InputMediaPhoto(open(file_path, "rb")))
        if media:
            await context.bot.send_media_group(chat_id=query.message.chat_id, media=media)
        await send_message_safe(context.bot, query.message.chat_id, "🌟 Обратная связь подписчиков 🌟", reply_markup=about_menu(include_reviews=False))
    elif data == "pay_tg":
        await send_message_safe(context.bot, query.message.chat_id, load_text("payment_trib"), reply_markup=payment_menu(exclude="pay_tg"))
    elif data == "pay_card_ru":
        await send_message_safe(context.bot, query.message.chat_id, load_text("payment_card_ru"), reply_markup=payment_menu(exclude="pay_card_ru"))
    elif data == "main":
        await send_message_safe(context.bot, query.message.chat_id, load_text("main"), reply_markup=main_menu())
    else:
        await send_message_safe(context.bot, query.message.chat_id, "⚠️ Неизвестная команда.", reply_markup=main_menu())

async def handle_text(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    txt = update.message.text.strip()
    await save_support_message(user.id, txt)
    await log_action(user.id, f"support_message: {txt}")
    await update.message.reply_text(
        "✅ Вопрос получен. Мы свяжемся с вами в личных сообщениях.",
        reply_markup=main_menu(),
        parse_mode='HTML'  # ✅ добавлено
    )

async def handle_media(update: Update, context: CallbackContext) -> None:
    message: Message = update.message
    user = message.from_user
    file_id = message.document.file_id if message.document else message.photo[-1].file_id
    tg_file = await context.bot.get_file(file_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original = tg_file.file_path.split("/")[-1]
    sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', original)
    filename = f"{timestamp}_{sanitized}"

    base_dir = BASE_DIR / "media" / "uploads" / str(user.id)
    base_dir.mkdir(parents=True, exist_ok=True)
    filepath = base_dir / filename

    await tg_file.download_to_drive(custom_path=str(filepath))

    with open(filepath, "rb") as f:
        await save_payment_upload(user.id, File(f))

    await log_action(user.id, f"uploaded_payment: {filename}")
    await update.message.reply_text(
        "✅ Чек получен. Проверим и добавим в канал.",
        parse_mode='HTML'  # ✅ добавлено на всякий случай
    )

async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    if hasattr(update, 'effective_message') and update.effective_message:
        await update.effective_message.reply_text("⚠️ Произошла ошибка. Попробуйте снова.")

def main() -> None:
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN_PRIVATE')).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_main_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_media))
    application.add_error_handler(error_handler)

    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()