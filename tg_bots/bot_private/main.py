from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
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
from dotenv import load_dotenv
import os

from core.models import TelegramClient, ClientAction, SupportMessage
from asgiref.sync import sync_to_async

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_text(name: str) -> str:
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "texts", f"{name}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return f"[текст '{name}' не найден]"


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подробнее о канале", callback_data="about")],
        [InlineKeyboardButton("💳 Способы оплаты", callback_data="payment")],
        [InlineKeyboardButton("✉ Задать вопрос", callback_data="support")]
    ])


def about_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌟 Отзывы", callback_data="reviews")],
        [InlineKeyboardButton("💳 Способы оплаты", callback_data="payment")],
        [InlineKeyboardButton("⬅️ На главную", callback_data="main")]
    ])


def payment_menu(exclude=None):
    buttons = []
    if exclude != "pay_tg":
        buttons.append([InlineKeyboardButton("📲 Телеграм", callback_data="pay_tg")])
    if exclude != "pay_card_ru":
        buttons.append([InlineKeyboardButton("💳 Карта РФ", callback_data="pay_card_ru")])
    buttons.append([InlineKeyboardButton("⬅️ На главную", callback_data="main")])
    return InlineKeyboardMarkup(buttons)


def back_to_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ На главную", callback_data="main")]
    ])


@sync_to_async
def save_telegram_user(user):
    TelegramClient.objects.get_or_create(
        user_id=user.id,
        defaults={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bot_source': 'private',
        }
    )


@sync_to_async
def log_action(user_id, action_name):
    client = TelegramClient.objects.filter(user_id=user_id).first()
    if client:
        ClientAction.objects.create(client=client, action=action_name)


@sync_to_async
def save_support_message(user_id, text):
    client = TelegramClient.objects.filter(user_id=user_id).first()
    if client:
        SupportMessage.objects.create(client=client, message=text)


async def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    await save_telegram_user(user)
    await log_action(user.id, "start_private")
    await update.message.reply_text(
        load_text("main"),
        reply_markup=main_menu()
    )


async def handle_main_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    await log_action(user.id, f"clicked_{data}")

    if data == "about":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=load_text("about"),
            reply_markup=about_menu()
        )

    elif data == "payment":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=load_text("payment"),
            reply_markup=payment_menu()
        )

    elif data == "support":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=load_text("support"),
            reply_markup=back_to_main()
        )

    elif data == "reviews":
        media_path = os.path.join(os.path.dirname(__file__), "media")
        media = []
        for i in range(1, 9):
            file_path = os.path.join(media_path, f"re{i}.jpg")
            if os.path.exists(file_path):
                media.append(InputMediaPhoto(open(file_path, "rb")))
        if media:
            await context.bot.send_media_group(chat_id=query.message.chat_id, media=media)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=load_text("reviews"),
            reply_markup=about_menu()
        )

    elif data == "pay_tg":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=load_text("payment_trib"),
            reply_markup=payment_menu(exclude="pay_tg")
        )

    elif data == "pay_card_ru":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=load_text("payment_card_ru"),
            reply_markup=payment_menu(exclude="pay_card_ru")
        )

    elif data == "main":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=load_text("main"),
            reply_markup=main_menu()
        )

    else:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Неизвестная команда.",
            reply_markup=main_menu()
        )


async def handle_text(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    txt = update.message.text.strip()
    await save_support_message(user.id, txt)
    await log_action(user.id, f"support_message: {txt}")
    await update.message.reply_text(
        "✅ Вопрос получен. Мы свяжемся с вами в личных сообщениях.",
        reply_markup=main_menu()
    )


async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    if hasattr(update, 'effective_message') and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте снова."
        )


def main() -> None:
    application = Application.builder().token(
        os.getenv('TELEGRAM_BOT_TOKEN_PRIVATE')
    ).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_main_menu))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_error_handler(error_handler)

    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()