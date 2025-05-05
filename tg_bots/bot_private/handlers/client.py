from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import CallbackContext
from bot.keyboards import (
    main_menu,
    currency_selection,
    delivery_methods,
    comment_options,
    confirm_buttons,
    get_menu_keyboard
)
from bot.states import *
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> int:
    """Обработка команды /start"""
    await update.message.reply_text(
        "Добро пожаловать!",
        reply_markup=get_menu_keyboard()
    )
    await show_main_menu(update)
    return MAIN_MENU

async def handle_text(update: Update, context: CallbackContext) -> int:
    """Обработка текстовых сообщений (кнопка Menu)"""
    text = update.message.text
    
    if text.lower() in ['menu', 'меню', '📋 menu']:
        await show_main_menu(update)
        return MAIN_MENU
    
    await update.message.reply_text(
        "Используйте кнопки меню для навигации",
        reply_markup=get_menu_keyboard()
    )
    return MAIN_MENU

async def show_main_menu(update: Update):
    """Показ главного меню"""
    text = "Главное меню:"
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=main_menu()
        )

async def handle_main_menu(update: Update, context: CallbackContext) -> int:
    """Обработка выбора в главном меню"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'create_order':
        context.user_data.clear()
        await query.edit_message_text(
            'Выберите валюту:',
            reply_markup=currency_selection()
        )
        return CURRENCY
    elif query.data == 'view_exchangers':
        return await show_offers(update, context)
    elif query.data == 'my_orders':
        await query.edit_message_text(
            "📋 Раздел 'Мои заявки' в разработке",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_menu')]
            ])
        )
    elif query.data == 'support':
        await query.edit_message_text(
            "🆘 Напишите нам @support_username",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_menu')]
            ])
        )
    elif query.data == 'back_to_menu':
        await show_main_menu(update)
    
    return MAIN_MENU

async def select_currency(update: Update, context: CallbackContext) -> int:
    """Обработка выбора валюты"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back':
        await show_main_menu(update)
        return MAIN_MENU
        
    context.user_data['currency_from'] = query.data
    await query.edit_message_text(
        f'Выбрана валюта: {query.data}\nВведите сумму:',
        reply_markup=None
    )
    return AMOUNT

async def get_amount(update: Update, context: CallbackContext) -> int:
    """Получение суммы"""
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError
            
        context.user_data['amount_from'] = amount
        await update.message.reply_text(
            'Выберите способ получения:',
            reply_markup=delivery_methods()
        )
        return METHOD
    except ValueError:
        await update.message.reply_text("❌ Введите число больше 0")
        return AMOUNT

async def select_method(update: Update, context: CallbackContext) -> int:
    """Выбор способа получения"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back':
        await query.edit_message_text(
            "Выберите валюту:",
            reply_markup=currency_selection()
        )
        return CURRENCY
        
    context.user_data['method'] = query.data
    await query.edit_message_text(
        "Добавить комментарий?",
        reply_markup=comment_options()
    )
    return COMMENT

async def enter_comment(update: Update, context: CallbackContext) -> int:
    """Запрос комментария"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back':
        await query.edit_message_text(
            "Выберите способ получения:",
            reply_markup=delivery_methods()
        )
        return METHOD
        
    await query.edit_message_text("Введите комментарий:")
    return COMMENT

async def handle_text_comment(update: Update, context: CallbackContext) -> int:
    """Обработка текстового комментария"""
    context.user_data['comment'] = update.message.text
    return await show_confirmation(update, context)

async def skip_comment(update: Update, context: CallbackContext) -> int:
    """Пропуск комментария"""
    query = update.callback_query
    await query.answer()
    context.user_data['comment'] = ""
    return await show_confirmation(update, context)

async def show_confirmation(update: Update, context: CallbackContext) -> int:
    """Показ подтверждения заявки"""
    try:
        if update.message:
            message = update.message
        elif update.callback_query and update.callback_query.message:
            message = update.callback_query.message
        else:
            logger.error("Не удалось получить сообщение для подтверждения")
            return MAIN_MENU

        confirmation_text = (
            '✅ Заявка готова!\n\n'
            f'Валюта: {context.user_data["currency_from"]}\n'
            f'Сумма: {context.user_data["amount_from"]}\n'
            f'Способ: {context.user_data["method"]}\n'
        )
        
        if context.user_data.get('comment'):
            confirmation_text += f'Комментарий: {context.user_data["comment"]}\n\n'
        
        await message.reply_text(
            confirmation_text,
            reply_markup=confirm_buttons()
        )
        return CONFIRM
        
    except Exception as e:
        logger.error(f"Ошибка в show_confirmation: {e}")
        return MAIN_MENU

async def confirm_exchange(update: Update, context: CallbackContext) -> int:
    """Подтверждение заявки"""
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm':
        await query.edit_message_text('✅ Заявка успешно отправлена!')
        await show_main_menu(update)
        return MAIN_MENU
    elif query.data == 'edit':
        context.user_data.clear()
        await query.edit_message_text(
            'Выберите валюту:',
            reply_markup=currency_selection()
        )
        return CURRENCY
    elif query.data == 'back':
        await query.edit_message_text(
            "Добавить комментарий?",
            reply_markup=comment_options()
        )
        return COMMENT

async def cancel(update: Update, context: CallbackContext) -> int:
    """Отмена диалога"""
    await update.message.reply_text('❌ Операция отменена')
    await show_main_menu(update)
    return MAIN_MENU

async def show_offers(update: Update, context: CallbackContext) -> int:
    """Показ доступных предложений"""
    try:
        query = update.callback_query
        await query.answer()
        
        offers = [
            {'id': 1, 'rate': 35.5, 'methods': ['bank', 'cash'], 'min': 100, 'max': 1000},
            {'id': 2, 'rate': 35.3, 'methods': ['crypto'], 'min': 50, 'max': 500}
        ]
        
        offer_text = "🏦 Доступные обменники:\n\n"
        for offer in offers:
            offer_text += (
                f"💰 Курс: {offer['rate']} THB\n"
                f"💵 Лимиты: {offer['min']}-{offer['max']} USDT\n"
                f"🏦 Методы: {', '.join(offer['methods'])}\n"
                f"--------------------------\n"
            )
        
        await query.edit_message_text(
            text=offer_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ В главное меню", callback_data='back_to_menu')]
            ])
        )
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Ошибка при показе предложений: {e}")
        await show_main_menu(update)
        return MAIN_MENU