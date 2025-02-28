from telebot import types
from config.config import ADMIN_IDS

# Главное меню с инлайн кнопками
def create_main_menu(user_id):
    markup = types.InlineKeyboardMarkup()

    # Раздел калькулятора
    calculator_button = types.InlineKeyboardButton(text="📦 Калькулятор", callback_data="calculator")
    markup.add(calculator_button)

    # Узнать курс юаня
    get_rate_button = types.InlineKeyboardButton(text="💹 Узнать курс юаня", callback_data="get_rate")
    markup.add(get_rate_button)

    faq_button = types.InlineKeyboardButton(text="📞 FAQ", callback_data="faq")
    markup.add(faq_button)

    info_button = types.InlineKeyboardButton(text="📞 О нас", callback_data="info")
    markup.add(info_button)

    # Связь с поддержкой
    support_button = types.InlineKeyboardButton(text="📞 Связь с поддержкой", url="https://t.me/destockhelp")
    markup.add(support_button)

    # Админ раздел (только для администраторов)
    if user_id in ADMIN_IDS:
        admin_button = types.InlineKeyboardButton(text="⚙️ Админ раздел", callback_data="admin_panel")
        markup.add(admin_button)

    return markup

# Меню калькулятора (с подменю для расчета стоимости, доставки и моих расчетов)
def create_calculator_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="💰 Расчет стоимости", callback_data="product_cost"))
    markup.add(types.InlineKeyboardButton(text="📦 Расчет доставки", callback_data="shipping_cost"))
    markup.add(types.InlineKeyboardButton(text="🧮 Мои расчеты", callback_data="my_calculations"))
    markup.add(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return markup

# Меню моих расчетов (с подменю для расчета стоимости и доставки)
def create_my_calculations_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="📊 Расчеты стоимости", callback_data="my_product_costs"))
    markup.add(types.InlineKeyboardButton(text="📦 Расчеты доставки", callback_data="my_shipping_costs"))
    markup.add(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return markup

# Меню админа (оставляем только установку курса)
def create_admin_panel_menu():
    markup = types.InlineKeyboardMarkup()

    # Кнопка для подменю "Установить курс"
    markup.add(types.InlineKeyboardButton(text="💹 Установить курс", callback_data="set_rate_menu"))

    # Если нужно добавить другие кнопки для админа

    markup.add(types.InlineKeyboardButton(text="Создать рассылку", callback_data="create_mailing"))

    markup.add(types.InlineKeyboardButton(text="Назначить администратора", callback_data="new_admin"))

    markup.add(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))

    return markup

def set_rate_menu_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="💵 Установить курс доллара", callback_data="set_usd_rate"))
    markup.add(types.InlineKeyboardButton(text="💴 Установить курс юаня", callback_data="set_cny_rate"))
    markup.add(types.InlineKeyboardButton(text="⚙️ Админ меню", callback_data="admin_panel"))
    return markup 

def create_exit_to_admin_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="⚙️ Админ меню", callback_data="admin_panel"))
    return markup
