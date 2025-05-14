from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_menu_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📋 Menu")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("О канале подробнее", callback_data='info')],
        [InlineKeyboardButton("Обо мне", callback_data='about')],
        [InlineKeyboardButton("Подписка", callback_data='sub')],
        [InlineKeyboardButton("F.A.Q спроси меня", callback_data='supp')]
    ])
