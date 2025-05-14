from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot.states import *
from bot.keyboards import offer_methods_keyboard, offer_confirmation_keyboard

async def start_offer_creation(update: Update, context: CallbackContext) -> int:
    """Начало создания предложения"""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()  # Очищаем предыдущие данные
    await query.edit_message_text("Введите курс обмена (например: 35.5):")
    return OFFER_STATE_RATE

async def handle_offer_rate(update: Update, context: CallbackContext) -> int:
    """Обработка введенного курса"""
    try:
        rate = float(update.message.text)
        if rate <= 0:
            raise ValueError
        context.user_data['offer_rate'] = rate
        await update.message.reply_text("Введите мин. и макс. сумму через пробел (например: 100 1000):")
        return OFFER_STATE_MIN_MAX
    except ValueError:
        await update.message.reply_text("❌ Введите положительное число (например: 35.5)")
        return OFFER_STATE_RATE

async def handle_offer_amounts(update: Update, context: CallbackContext) -> int:
    """Обработка лимитов суммы"""
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            raise ValueError
            
        min_amount, max_amount = map(float, parts)
        if min_amount <= 0 or max_amount <= 0 or min_amount > max_amount:
            raise ValueError
            
        context.user_data['offer_min'] = min_amount
        context.user_data['offer_max'] = max_amount
        context.user_data['offer_methods'] = []  # Инициализируем список методов
        
        await update.message.reply_text(
            "Выберите методы оплаты:",
            reply_markup=offer_methods_keyboard()
        )
        return OFFER_STATE_METHODS
    except Exception as e:
        await update.message.reply_text("❌ Введите два положительных числа через пробел (мин макс), где мин <= макс")
        return OFFER_STATE_MIN_MAX

async def handle_offer_methods(update: Update, context: CallbackContext) -> int:
    """Обработка выбора методов оплаты"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back':
        await query.edit_message_text("Введите мин. и макс. сумму через пробел:")
        return OFFER_STATE_MIN_MAX
        
    if query.data == 'method_done':
        if not context.user_data.get('offer_methods'):
            await query.answer("❌ Выберите хотя бы один метод!", show_alert=True)
            return OFFER_STATE_METHODS
            
        methods_str = ', '.join(context.user_data['offer_methods'])
        await query.edit_message_text(
            f"✅ Предложение готово!\n\n"
            f"Курс: {context.user_data['offer_rate']}\n"
            f"Лимиты: {context.user_data['offer_min']}-{context.user_data['offer_max']}\n"
            f"Методы: {methods_str}",
            reply_markup=offer_confirmation_keyboard()
        )
        return OFFER_CONFIRM
        
    # Обработка выбора метода
    method = query.data.replace('method_', '')
    if method in context.user_data['offer_methods']:
        context.user_data['offer_methods'].remove(method)
    else:
        context.user_data['offer_methods'].append(method)
    
    await query.edit_message_text(
        "Выберите методы оплаты:",
        reply_markup=offer_methods_keyboard(context.user_data['offer_methods'])
    )
    return OFFER_STATE_METHODS

async def confirm_offer(update: Update, context: CallbackContext) -> int:
    """Подтверждение предложения"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'publish_offer':
        # Здесь сохраняем предложение в БД
        await query.edit_message_text("✅ Предложение успешно опубликовано!")
    elif query.data == 'edit_offer':
        await query.edit_message_text(
            "Выберите методы оплаты:",
            reply_markup=offer_methods_keyboard(context.user_data['offer_methods'])
        )
        return OFFER_STATE_METHODS
    else:  # cancel_offer
        await query.edit_message_text("❌ Создание предложения отменено")
    
    return ConversationHandler.END