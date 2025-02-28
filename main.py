import telebot
from telebot import types
import logging
import matplotlib.pyplot as plt
from config.config import API_TOKEN, ADMIN_IDS, CHANNEL_USERNAME
from keyboard.keyboard import create_main_menu, create_calculator_menu, create_admin_panel_menu, create_exit_to_admin_button, create_my_calculations_menu, set_rate_menu_markup
from database.database import create_db, save_user_history, get_user_history, save_yuan_rate_graph
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler
from telegram.ext.filters import Command, Text
from functools import partial
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO
import os
import time
import sqlite3

bot = telebot.TeleBot(API_TOKEN)

# Настроим логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Глобальная переменная для хранения курса доллара и юаня
usd_rate = 1.0  # Курс доллара (устанавливается администратором)
cny_rate = 12.0  # Курс юаня (устанавливается администратором)

user_data = {}
user_history = {}
orders_data = {}

# Инициализируем базу данных
create_db()

def is_subscribed(user_id):
    try:
        # Получаем информацию о пользователе в канале
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        
        # Проверяем, состоит ли пользователь в канале
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Ошибка при проверке подписки для {user_id}: {e}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Проверяем, подписан ли пользователь на канал
    if not is_subscribed(user_id):  # Здесь будет ваша логика для проверки подписки
        markup = types.InlineKeyboardMarkup()
        subscribe_button = types.InlineKeyboardButton(text="✅ Подписаться", url=f"t.me/{CHANNEL_USERNAME}")
        check_subscription_button = types.InlineKeyboardButton(text="🔍 Проверить подписку", callback_data="check_subscription")
        markup.add(subscribe_button, check_subscription_button)
        
        # Отправляем изображение для подписки, текст и инлайн кнопки в одном сообщении
        with open('Images/subscribe.jpg', 'rb') as photo:  # Изображение для проверки подписки
            bot.send_photo(
                message.chat.id, 
                photo, 
                caption="Для использования бота необходимо подписаться на канал.",
                reply_markup=markup  # Добавляем инлайн кнопки
            )
        return

    logging.info(f"Пользователь {user_id} запустил бота.")
    
    # Если подписан, отправляем изображение для главного меню, текст и инлайн кнопки в одном сообщении
    with open('Images/mm3.jpg', 'rb') as photo:  # Изображение для главного меню
        bot.send_photo(
            message.chat.id, 
            photo, 
            caption="Добро пожаловать! Выберите одну из опций.",
            reply_markup=create_main_menu(user_id)  # Передаем user_id для создания главного меню
        )

# Логика для расчета стоимости доставки
@bot.callback_query_handler(func=lambda call: call.data == "shipping_cost")
def start_shipping_calculation(call):
    """Запрашиваем у пользователя название расчета перед вводом данных"""
    user_id = call.from_user.id
    user_data[user_id] = {}  # Создаем запись для пользователя

    # Удаляем старое сообщение с меню калькулятора
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Отправляем картинку "search_ship" и запрашиваем название расчета
    with open('Images/search_ship.jpg', 'rb') as photo:
        sent_message = bot.send_photo(call.message.chat.id, photo, caption="Введите название расчета:")

    user_data[user_id]['last_bot_message_id'] = sent_message.message_id
    bot.register_next_step_handler(call.message, process_calc_name)


def process_calc_name(message):
    """Обрабатываем ввод названия расчета"""
    user_id = message.from_user.id

    # Удаляем прошлые сообщения
    delete_previous_messages(message.chat.id, user_id, message.message_id)

    user_data[user_id]['calc_name'] = message.text  # Сохраняем название расчета

    # Отправляем запрос длины товара
    with open('Images/search_ship.jpg', 'rb') as photo:
        sent_message = bot.send_photo(message.chat.id, photo, caption="Введите длину товара в см:")

    user_data[user_id]['last_bot_message_id'] = sent_message.message_id
    bot.register_next_step_handler(message, process_length)

def process_length(message):
    """Обрабатываем ввод длины товара"""
    user_id = message.from_user.id
    try:
        user_data[user_id]['length'] = float(message.text)

        delete_previous_messages(message.chat.id, user_id, message.message_id)

        with open('Images/search_ship.jpg', 'rb') as photo:
            sent_message = bot.send_photo(message.chat.id, photo, caption="Введите ширину товара в см:")

        user_data[user_id]['last_bot_message_id'] = sent_message.message_id
        bot.register_next_step_handler(message, process_width)

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите число.")


def process_width(message):
    """Обрабатываем ввод ширины товара"""
    user_id = message.from_user.id
    try:
        user_data[user_id]['width'] = float(message.text)

        delete_previous_messages(message.chat.id, user_id, message.message_id)

        with open('Images/search_ship.jpg', 'rb') as photo:
            sent_message = bot.send_photo(message.chat.id, photo, caption="Введите высоту товара в см:")

        user_data[user_id]['last_bot_message_id'] = sent_message.message_id
        bot.register_next_step_handler(message, process_height)

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите число.")


def process_height(message):
    """Обрабатываем ввод высоты товара"""
    user_id = message.from_user.id
    try:
        user_data[user_id]['height'] = float(message.text)

        delete_previous_messages(message.chat.id, user_id, message.message_id)

        with open('Images/search_ship.jpg', 'rb') as photo:
            sent_message = bot.send_photo(message.chat.id, photo, caption="Введите вес товара в кг:")

        user_data[user_id]['last_bot_message_id'] = sent_message.message_id
        bot.register_next_step_handler(message, process_weight)

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите число.")


def process_weight(message):
    """Обрабатываем ввод веса товара и запрашиваем подтверждение"""
    user_id = message.from_user.id
    try:
        user_data[user_id]['weight'] = float(message.text)

        delete_previous_messages(message.chat.id, user_id, message.message_id)

        confirm_shipping_data(message)

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите число.")


def confirm_shipping_data(message):
    """Выводим подтверждение введенных данных"""
    user_id = message.from_user.id
    data = user_data[user_id]

    response = (
        f"*Название расчета:* {data['calc_name']}\n\n"
        f"📏 Длина: {data['length']} см\n"
        f"📐 Ширина: {data['width']} см\n"
        f"📦 Высота: {data['height']} см\n"
        f"⚖️ Вес: {data['weight']} кг\n\n"
        f"Нажмите ✅ *Подтвердить* или ❌ *Изменить*."
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_shipping_calc"))
    markup.add(types.InlineKeyboardButton("❌ Изменить", callback_data="shipping_cost"))

    sent_message = bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)
    user_data[user_id]['last_bot_message_id'] = sent_message.message_id


@bot.callback_query_handler(func=lambda call: call.data == "confirm_shipping_calc")
def calculate_shipping(call):
    """Рассчитываем стоимость доставки"""
    user_id = call.from_user.id
    data = user_data[user_id]

    volume_weight = (data['length'] * data['width'] * data['height']) / 5000  
    normal_weight = data['weight']
    final_weight = max(volume_weight, normal_weight)

    cost_in_usd = final_weight * 9  
    cost_in_rub = cost_in_usd * usd_rate  
    cost_in_cny = cost_in_rub / cny_rate  

    response = (
        f"📦 *Название расчета:* {data['calc_name']}\n\n"
        f"📏 Длина: {data['length']} см\n"
        f"📐 Ширина: {data['width']} см\n"
        f"📦 Высота: {data['height']} см\n"
        f"⚖️ Реальный вес: {normal_weight:.2f} кг\n"
        f"⚖️ Объемный вес: {volume_weight:.2f} кг\n"
        f"🔹 *Итоговый расчетный вес:* {final_weight:.2f} кг\n\n"
        f"💲 Стоимость доставки: {cost_in_usd:.2f} $\n"
        f"💵 Стоимость в рублях: {cost_in_rub:.2f} ₽\n"
        f"💴 Стоимость в юанях: {cost_in_cny:.2f} ¥"
    )

    time.sleep(5)
    delete_previous_messages(call.message.chat.id, user_id, call.message.message_id)

    with open('Images/search_ship.jpg', 'rb') as photo:
        bot.send_photo(call.message.chat.id, photo, caption=response, reply_markup=create_exit_button())

    # **Сохраняем расчет в базу данных**
    save_calculation_to_db(user_id, data['calc_name'], "shipping_cost", response)


def save_calculation_to_db(user_id, calc_name, calc_type, result):
    """Функция сохранения расчета в базу данных"""
    print(f"Сохранение в БД: {user_id}, {calc_name}, {calc_type}, {result}")
#

###

# Обработчик для кнопки "💰 Расчет стоимости"
@bot.callback_query_handler(func=lambda call: call.data == "product_cost")
def start_product_calculation(call):
    """Запрашиваем у пользователя название расчета перед вводом данных"""
    user_id = call.from_user.id
    user_data[user_id] = {}  # Создаем запись для пользователя

    # Удаляем старое сообщение с меню калькулятора
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Отправляем картинку "search_order.jpg" и запрашиваем название расчета
    with open('Images/search_order.jpg', 'rb') as photo:
        sent_message = bot.send_photo(call.message.chat.id, photo, caption="Введите название расчета:")

    user_data[user_id]['last_bot_message_id'] = sent_message.message_id
    bot.register_next_step_handler(call.message, process_calculation_name)


def process_calculation_name(message):
    """Обрабатываем ввод названия расчета"""
    user_id = message.from_user.id

    # Удаляем прошлые сообщения
    delete_previous_messages(message.chat.id, user_id, message.message_id)

    user_data[user_id]['calc_name'] = message.text.strip()  # Сохраняем название

    if not user_data[user_id]['calc_name']:
        bot.send_message(message.chat.id, "Ошибка: название не может быть пустым. Введите название.")
        return

    # Запрашиваем стоимость товара в юанях
    with open('Images/search_order.jpg', 'rb') as photo:
        sent_message = bot.send_photo(message.chat.id, photo, caption="Введите стоимость товара в юанях:")

    user_data[user_id]['last_bot_message_id'] = sent_message.message_id
    bot.register_next_step_handler(message, process_price_in_cny)


def delete_previous_messages(chat_id, user_id, user_message_id):
    """Удаляет два последних сообщения (бота и пользователя)"""
    try:
        if 'last_bot_message_id' in user_data[user_id]:
            bot.delete_message(chat_id, user_data[user_id]['last_bot_message_id'])  # Удаляем сообщение бота
        bot.delete_message(chat_id, user_message_id)  # Удаляем сообщение пользователя
    except Exception as e:
        print(f"Ошибка при удалении сообщений: {e}")


def process_price_in_cny(message):
    """Обрабатываем ввод стоимости товара в юанях"""
    user_id = message.from_user.id
    try:
        user_data[user_id]['price_in_cny'] = float(message.text)

        delete_previous_messages(message.chat.id, user_id, message.message_id)
        confirm_product_cost_data(message)

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите число.")


def confirm_product_cost_data(message):
    """Выводим подтверждение введенных данных перед расчетом"""
    user_id = message.from_user.id
    data = user_data[user_id]

    response = (
        f"*Название расчета:* {data['calc_name']}\n\n"
        f"💰 *Стоимость в юанях:* {data['price_in_cny']} юаней\n"
        f"Нажмите ✅ *Подтвердить* или ❌ *Изменить*."
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_product_cost_calc"))
    markup.add(types.InlineKeyboardButton("❌ Изменить", callback_data="product_cost"))

    sent_message = bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)
    user_data[user_id]['last_bot_message_id'] = sent_message.message_id


@bot.callback_query_handler(func=lambda call: call.data == "confirm_product_cost_calc")
def calculate_product_cost(call):
    """Рассчитываем стоимость товара с учетом комиссии"""
    user_id = call.from_user.id
    data = user_data[user_id]

    price_in_cny = data['price_in_cny']

    # Определяем процент комиссии
    if price_in_cny <= 300:
        commission_percent = 15
    elif price_in_cny <= 500:
        commission_percent = 10
    else:
        commission_percent = 5

    # Рассчитываем комиссию
    commission_in_cny = price_in_cny * (commission_percent / 100)
    commission_in_rub = commission_in_cny * cny_rate

    # Итоговая стоимость
    price_in_rub = price_in_cny * cny_rate
    final_cost = price_in_rub + commission_in_rub

    response = (
        f"📦 *Название расчета:* {data['calc_name']}\n\n"
        f"💰 *Стоимость товара в юанях:* {price_in_cny} юаней\n"
        f"💵 *Стоимость в рублях (по курсу {cny_rate}):* {price_in_rub:.2f} ₽\n"
        f"📊 *Комиссия ({commission_percent}%):* {commission_in_rub:.2f} ₽\n"
        f"💲 *Итоговая стоимость:* {final_cost:.2f} ₽"
    )

    time.sleep(5)
    delete_previous_messages(call.message.chat.id, user_id, call.message.message_id)

    with open('Images/search_order.jpg', 'rb') as photo:
        bot.send_photo(call.message.chat.id, photo, caption=response, reply_markup=create_exit_button())

    # **Сохраняем расчет в базу данных**
    save_calculation_to_db(user_id, data['calc_name'], "product_cost", response)


def save_calculation_to_db(user_id, calc_name, calc_type, result):
    """Функция сохранения расчета в базу данных"""
    
    # Время сохранения расчета
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Сохраняем данные в базу данных
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO calculations (user_id, calc_name, calc_type, result, timestamp)
                          VALUES (?, ?, ?, ?, ?)''', 
                          (user_id, calc_name, calc_type, result, timestamp))
        conn.commit()
    
    # Выводим в консоль для отладки
    print(f"Сохранение в БД: {user_id}, {calc_name}, {calc_type}, {result}")

    

###

@bot.callback_query_handler(func=lambda call: call.data == "my_calculations")
def my_calculations(call):
    # Отправляем картинку "archive.jpg" перед меню
    with open('Images/archive.jpg', 'rb') as photo:  # Путь к картинке
        # Получаем готовое меню из keyboard.py
        markup = create_my_calculations_menu()

        # Отправляем фото с меню
        bot.send_photo(call.message.chat.id, photo, caption="Выберите тип ваших расчетов:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "my_product_costs")
def show_product_costs(call):
    user_history = get_user_history(call.from_user.id)

    # Фильтруем только расчеты для стоимости товара
    product_costs = [record for record in user_history if record[0] == "Стоимость товара"]

    # Инициализируем клавиатуру
    markup = types.InlineKeyboardMarkup()

    if not product_costs:
        bot.send_message(call.message.chat.id, "История расчетов пуста.", reply_markup=create_calculator_menu())
    else:
        response = "📊 История расчетов стоимости товара:\n"

        # Добавляем кнопки для последних 5 расчетов
        for i, record in enumerate(product_costs[:5]):
            markup.add(types.InlineKeyboardButton(text=f"Расчет {i+1}", callback_data=f"view_product_cost_{i}"))

        # Отправляем сообщение с кнопками
        bot.send_message(call.message.chat.id, response, reply_markup=markup)

    # Добавляем кнопку возврата
    markup.add(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    bot.send_message(call.message.chat.id, "Выберите другой расчет или вернитесь в главное меню.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_product_cost_"))
def view_product_cost(call):
    calc_index = int(call.data.split("_")[-1])

    # Получаем историю расчетов
    user_history = get_user_history(call.from_user.id)
    product_costs = [record for record in user_history if record[0] == "Стоимость товара"]

    if calc_index < len(product_costs):
        response = f"📊 Подробности расчета:\n{product_costs[calc_index][1]}"
        bot.send_message(call.message.chat.id, response, reply_markup=create_calculator_menu())
    else:
        bot.answer_callback_query(call.id, "Расчет не найден.")

    # Кнопка возврата
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    bot.send_message(call.message.chat.id, "Выберите другой расчет или вернитесь в главное меню.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "my_shipping_costs")
def show_shipping_costs(call):
    user_history = get_user_history(call.from_user.id)

    # Фильтруем только расчеты для стоимости доставки
    shipping_costs = [record for record in user_history if record[0] == "Стоимость доставки"]

    markup = types.InlineKeyboardMarkup()

    if not shipping_costs:
        bot.send_message(call.message.chat.id, "История расчетов пуста.", reply_markup=create_calculator_menu())
    else:
        response = "📦 История расчетов стоимости доставки:\n"
        for i, record in enumerate(shipping_costs[:5]):
            markup.add(types.InlineKeyboardButton(text=f"Доставка {i+1}", callback_data=f"view_shipping_cost_{i}"))

        bot.send_message(call.message.chat.id, response, reply_markup=markup)

    # Добавляем кнопку возврата в главное меню
    markup.add(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    bot.send_message(call.message.chat.id, "Выберите другой расчет или вернитесь в главное меню.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_shipping_cost_"))
def view_shipping_cost(call):
    """Обрабатываем запрос на просмотр подробностей расчета стоимости доставки"""
    try:
        # Извлекаем индекс расчета
        calc_index = int(call.data.split("_")[-1])

        # Получаем историю расчетов пользователя
        user_history = get_user_history(call.from_user.id)
        shipping_costs = [record for record in user_history if record[0] == "Стоимость доставки"]

        # Проверка, что индекс существует в списке
        if calc_index < len(shipping_costs):
            response = f"📦 Подробности расчета:\n{shipping_costs[calc_index][1]}"

            # Отправляем новое сообщение с подробностями
            bot.send_message(call.message.chat.id, response, reply_markup=create_calculator_menu())
        else:
            bot.answer_callback_query(call.id, "Расчет не найден.")

    except Exception as e:
        # Обработка любых ошибок (например, если индексы не совпадают)
        bot.answer_callback_query(call.id, "Произошла ошибка при получении расчета.")
        print(f"Ошибка в обработчике: {e}")

# Функция проверки админа
def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    """Удаляет предыдущее сообщение и отправляет админ-панель с изображением"""
    bot.delete_message(call.message.chat.id, call.message.message_id)

    if is_admin(call.from_user.id):  # Проверка, является ли пользователь администратором
        with open('Images/admin.jpg', 'rb') as photo:
            markup = create_admin_panel_menu()  # Создаем меню админа
            bot.send_photo(call.message.chat.id, photo, caption="Добро пожаловать в админ-панель", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "❌ У вас нет прав для доступа к админскому разделу.")

@bot.callback_query_handler(func=lambda call: call.data == "set_rate_menu")
def set_rate_menu(call):
    """Удаляет предыдущее сообщение и отправляет меню установки курса с изображением"""
    try:
        # Удаляем предыдущее сообщение
        bot.delete_message(call.message.chat.id, call.message.message_id)

        # Проверяем, является ли пользователь администратором
        if is_admin(call.from_user.id):
            # Отправляем изображение с кнопками
            with open('Images/new_course.jpg', 'rb') as photo:
                # Отправляем изображение с меню
                bot.send_photo(call.message.chat.id, photo, caption="Выберите курс для установки:", reply_markup=set_rate_menu_markup())
        else:
            # Если пользователь не является администратором
            bot.send_message(call.message.chat.id, "❌ У вас нет прав для доступа к этой функции.")
    except FileNotFoundError:
        # Ошибка, если изображение не найдено
        bot.send_message(call.message.chat.id, "Ошибка: изображение для меню не найдено.")
    except Exception as e:
        # Общая обработка ошибок
        bot.send_message(call.message.chat.id, f"Произошла ошибка: {e}")
        # Логирование ошибки в консоль для отладки
        print(f"Ошибка при обработке set_rate_menu: {e}")

# Обработчик для кнопки "💵 Установить курс доллара"

# Обработчик для кнопки "💵 Установить курс доллара"

@bot.callback_query_handler(func=lambda call: call.data == "set_usd_rate")
def set_usd_rate(call):
    """Запрашиваем новый курс доллара"""
    user_id = call.from_user.id
    user_data[user_id] = {}  # Создаем запись для пользователя

    # Удаляем старое сообщение с меню установки курса
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Отправляем картинку и запрашиваем новый курс доллара
    with open('Images/new_course_usd.jpg', 'rb') as photo:
        sent_message = bot.send_photo(call.message.chat.id, photo, caption="Введите новый курс доллара:")

    user_data[user_id]['last_bot_message_id'] = sent_message.message_id
    bot.register_next_step_handler(call.message, process_rate)


def process_rate(message):
    """Обрабатываем ввод нового курса доллара"""
    user_id = message.from_user.id

    # Удаляем прошлые сообщения
    delete_previous_messages(message.chat.id, user_id, message.message_id)

    try:
        # Обрабатываем введенный курс
        rate = float(message.text)

        # Обновляем глобальную переменную usd_rate
        global usd_rate
        usd_rate = rate  # Присваиваем новое значение переменной usd_rate

        # Сохраняем новый курс доллара в базу данных
        save_valute_rate("USD", rate, "Обновление курса на {}".format(datetime.today().strftime('%Y-%m-%d')))

        # Отправляем сообщение с подтверждением и картинкой
        with open('Images/new_course_successfully.jpg', 'rb') as success_photo:
            sent_message = bot.send_photo(message.chat.id, success_photo, 
                                          caption=f"Курс доллара установлен: {rate} руб.\nДля выхода в главное меню, нажмите кнопку ниже.",
                                          reply_markup=create_exit_to_admin_button())

        user_data[user_id]['last_bot_message_id'] = sent_message.message_id

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите правильное число.")

    bot.register_next_step_handler(message, process_rate)


def save_valute_rate(currency_code, rate, changes):
    """
    Сохраняет курс валюты в базу данных.
    """
    date = datetime.today().strftime('%Y-%m-%d')

    try:
        # Подключаемся к базе данных
        with sqlite3.connect('database/bot_data.db') as conn:
            cursor = conn.cursor()

            # Выполняем SQL-запрос для сохранения данных
            cursor.execute('''INSERT INTO valute (currency_code, rate, date, changes) 
                              VALUES (?, ?, ?, ?)''', 
                              (currency_code, rate, date, changes))

            # Сохраняем изменения в базе данных
            conn.commit()

        # Выводим в консоль для отладки
        print(f"Курс {currency_code} сохранен: {rate} на {date} с изменениями: {changes}")
    
    except sqlite3.Error as e:
        # Обработка ошибок SQLite
        print(f"Ошибка при сохранении курса в базу данных: {e}")

    except Exception as e:
        # Общая обработка ошибок
        print(f"Произошла ошибка: {e}")


def delete_previous_messages(chat_id, user_id, user_message_id):
    """Удаляет два последних сообщения (бота и пользователя)"""
    try:
        if 'last_bot_message_id' in user_data[user_id]:
            bot.delete_message(chat_id, user_data[user_id]['last_bot_message_id'])  # Удаляем сообщение бота
        bot.delete_message(chat_id, user_message_id)  # Удаляем сообщение пользователя
    except Exception as e:
        print(f"Ошибка при удалении сообщений: {e}")



@bot.callback_query_handler(func=lambda call: call.data == "set_cny_rate")
def set_cny_rate(call):
    """Запрашивает новый курс юаня"""
    user_id = call.from_user.id
    user_data[user_id] = {}  # Создаем запись для пользователя

    # Удаляем старое сообщение с меню установки курса
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Отправляем картинку и запрашиваем новый курс юаня
    with open('Images/new_course_usd.jpg', 'rb') as photo:
        sent_message = bot.send_photo(call.message.chat.id, photo, caption="Введите новый курс юаня:")

    user_data[user_id]['last_bot_message_id'] = sent_message.message_id
    bot.register_next_step_handler(call.message, process_cny_rate)


def process_cny_rate(message):
    """Обрабатываем ввод нового курса юаня"""
    user_id = message.from_user.id

    # Удаляем прошлые сообщения
    delete_previous_messages(message.chat.id, user_id, message.message_id)

    try:
        # Обрабатываем введенный курс
        rate = float(message.text)

        # Обновляем глобальную переменную cny_rate
        global cny_rate
        cny_rate = rate  # Присваиваем новое значение переменной cny_rate

        # Сохраняем новый курс юаня в базу данных
        save_valute_rate("CNY", rate, "Обновление курса на {}".format(datetime.today().strftime('%Y-%m-%d')))

        # Отправляем сообщение с подтверждением и картинкой
        with open('Images/new_course_successfully.jpg', 'rb') as success_photo:
            sent_message = bot.send_photo(message.chat.id, success_photo, 
                                          caption=f"Курс юаня установлен: {rate} руб.\nДля выхода в главное меню, нажмите кнопку ниже.",
                                          reply_markup=create_exit_to_admin_button())

        user_data[user_id]['last_bot_message_id'] = sent_message.message_id

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите правильное число.")

    bot.register_next_step_handler(message, process_cny_rate)

def generate_rate_image():
    """Генерация изображения с курсами валют и логотипом"""
    
    # Получаем актуальные курсы валют из базы данных
    usd_rate = get_valute_rate("USD")  # Получаем курс доллара
    cny_rate = get_valute_rate("CNY")  # Получаем курс юаня

    if usd_rate is None:
        usd_rate = 85.0  # Если курс не найден, ставим дефолтное значение
    if cny_rate is None:
        cny_rate = 12.3  # Если курс не найден, ставим дефолтное значение

    # Создаем изображение
    img = Image.new('RGB', (400, 200), color=(206, 204, 205))
    d = ImageDraw.Draw(img)

    # Загружаем шрифт
    try:
        font = ImageFont.truetype("fonts/Typingrad.otf", 30)
    except IOError:
        font = ImageFont.load_default()

    today = datetime.today().strftime('%Y-%m-%d')

    # Добавляем текст с курсами
    d.text((10, 10), f"Курс доллара: {usd_rate} руб.", font=font, fill=(0, 0, 0))
    d.text((10, 60), f"Курс юаня: {cny_rate} руб.", font=font, fill=(0, 0, 0))
    d.text((10, 110), f"Дата: {today}", font=font, fill=(0, 0, 0))

    # Загружаем лого
    logo_path = "Images/logo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = (80, 80)
            logo = logo.resize(logo_size, Image.LANCZOS)
            logo_x = img.width - logo_size[0] - 10
            logo_y = img.height - logo_size[1] - 10
            img.paste(logo, (logo_x, logo_y), mask=logo)
        except Exception as e:
            print(f"Ошибка при загрузке логотипа: {e}")
    else:
        print("Логотип не найден, использую стандартное изображение")

    # Сохранение изображения в поток
    image_stream = BytesIO()
    img.save(image_stream, format='PNG')
    image_stream.seek(0)

    return image_stream

@bot.callback_query_handler(func=lambda call: call.data == "get_rate")
def send_rate_image(call):
    """Удаляем старое сообщение, затем отправляем изображение с курсами"""
    
    # Удаляем старое сообщение с меню
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Генерация изображения с курсами валют
    image_stream = generate_rate_image()

    # Отправляем одно сообщение с изображением курса валют и текстом в caption
    sent_message = bot.send_photo(call.message.chat.id, image_stream, 
                                  caption="📊 Курс валют:\nЗдесь находится ваш запрос по курсу валют. 📊", 
                                  reply_markup=create_exit_button())

def get_valute_rate(currency_code):
    """Получаем курс валюты из базы данных"""
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT rate FROM valute WHERE currency_code = ? ORDER BY date DESC LIMIT 1''', (currency_code,))
        result = cursor.fetchone()

    if result:
        return result[0]  # Возвращаем курс валюты
    else:
        return None  # Если данных нет, возвращаем None
##

@bot.callback_query_handler(func=lambda call: call.data == "calculator")
def show_calculator(call):
    # Удаляем старое сообщение с кнопкой "📦 Калькулятор"
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Отправляем картинку "calculator.jpg" вместе с меню калькулятора
    with open('Images/calculator.jpg', 'rb') as photo:  # Путь к картинке
        markup = create_calculator_menu()  # Получаем меню калькулятора

        # Отправляем фото и редактируем меню калькулятора
        bot.send_photo(call.message.chat.id, photo, caption="Выберите тип расчета:", reply_markup=markup)

    # Редактируем кнопку "📦 Калькулятор" в главном меню
    markup = create_main_menu(call.from_user.id)  # Создаем основное меню
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def return_to_main_menu(call):
    try:
        # Пробуем отредактировать сообщение (если возможно)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,  # ID текущего сообщения
            text="🏠 Добро пожаловать в главное меню!",  # Новый текст
            reply_markup=create_main_menu(call.from_user.id)  # Новые кнопки
        )

        # Пробуем редактировать картинку (если она требуется)
        with open('Images/main_menu_image.jpg', 'rb') as photo:  # Путь к картинке для главного меню
            bot.edit_message_media(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                media=types.InputMediaPhoto(photo)  # Новая картинка для главного меню
            )

    except Exception as e:
        # Если редактирование не получилось, удаляем старое сообщение и отправляем новое с изображением
        print(f"Ошибка при редактировании сообщения: {e}")
        
        # Удаляем старое сообщение, если оно существует
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as delete_error:
            print(f"Ошибка при удалении сообщения: {delete_error}")

        # Отправляем новое сообщение с главным меню и изображением
        with open('Images/mm3.jpg', 'rb') as photo:  # Путь к картинке для главного меню
            bot.send_photo(call.message.chat.id, photo, caption="🏠 Добро пожаловать в главное меню!", reply_markup=create_main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription(call):
    user_id = call.from_user.id
    
    if is_subscribed(user_id):
        bot.answer_callback_query(call.id, "Вы подписаны на канал!")
        bot.send_message(call.message.chat.id, "Спасибо за подписку! Теперь вы можете использовать бота.")
    else:
        bot.send_message(call.id, "Вы не подписаны на канал.")
        bot.send_message(call.message.chat.id, "Для использования бота необходимо подписаться на канал.")
        
    # Перезагружаем меню
    bot.send_message(call.message.chat.id, "Выберите одну из опций:", reply_markup=create_main_menu(user_id))

def create_exit_button():
    """Создает кнопку для выхода в главное меню"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return markup

if __name__ == '__main__':
    logging.info("Бот запущен")
bot.polling(none_stop=True, interval=0)
