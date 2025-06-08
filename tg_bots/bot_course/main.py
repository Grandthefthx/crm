from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
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

from core.models import TelegramClient
from asgiref.sync import sync_to_async

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("О канале подробнее", callback_data='info'),
            InlineKeyboardButton("Обо мне",           callback_data='about'),
        ],
        [
            InlineKeyboardButton("Подписка",          callback_data='sub'),
            InlineKeyboardButton("F.A.Q спроси меня", callback_data='supp'),
        ],
    ])

def flow_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 В поток", url="https://t.me/soul_evolucion")]
    ])

def read_greeting_text() -> str:
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, 'greeting.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Ошибка при чтении greeting.txt: {e}")
        return "Произошла ошибка при загрузке текста приветствия."

@sync_to_async
def save_telegram_user(user):
    TelegramClient.objects.get_or_create(
        user_id=user.id,
        defaults={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bot_source': 'public',
        }
    )

async def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    await save_telegram_user(user)

    text = update.message.text or ""
    args = text.split()
    param = args[1] if len(args) > 1 else None

    # Показываем "В поток" только при первом входе с ?start=flow
    if param == "flow" and not context.chat_data.get('flow_started'):
        context.chat_data['flow_started'] = True
        await update.message.reply_text(
            "Добро пожаловать в поток ✨\nНажми кнопку ниже, чтобы перейти в наш канал.",
            reply_markup=flow_keyboard()
        )
        return

    if not context.chat_data.get('greeting_sent'):
        text = read_greeting_text()
        await update.message.reply_text(
            text,
            reply_markup=main_menu()
        )
        context.chat_data['greeting_sent'] = True

async def handle_main_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'info':
        text = "📢 О канале подробнее: Здесь мы публикуем лучшие предложения!"
    elif query.data == 'about':
        text = "👤 Обо мне: Я бот, который помогает находить информацию!"
    elif query.data == 'sub':
        text = "🔔 Подписка: Подпишитесь, чтобы не пропустить новости!"
    elif query.data == 'supp':
        text = "❓ F.A.Q: Задайте вопрос, и я постараюсь помочь!"
    else:
        return await query.edit_message_reply_markup(reply_markup=main_menu())

    await query.edit_message_text(text)

async def handle_text(update: Update, context: CallbackContext) -> None:
    txt = update.message.text.strip().lower()
    if txt in ('меню', 'menu', '📋 menu'):
        await update.message.reply_text(
            "Выберите пункт:",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "Для навигации используйте меню:\nнапишите «меню» или нажмите кнопку.",
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
        os.getenv('TELEGRAM_BOT_TOKEN')
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
