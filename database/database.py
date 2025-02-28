import sqlite3
import os
import json
from datetime import datetime

# Путь к папке пользователей и валют
USERS_DIR = "database/users/"
VALUTE_DIR = "database/valute/"

import sqlite3
import os

def create_db():
    """Создает таблицы в базе данных."""
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()

        # Таблица для хранения информации о расчетах
        cursor.execute('''CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            calc_name TEXT NOT NULL,  -- Имя расчета
            calc_type TEXT NOT NULL,  -- Тип расчета (доставка, стоимость товара и т.д.)
            result TEXT NOT NULL,     -- Результат расчета (строка с результатом)
            timestamp TEXT NOT NULL   -- Время сохранения расчета
        );''')

        # Таблица для хранения курсов валют (доллар, юань и т.д.)
        cursor.execute('''CREATE TABLE IF NOT EXISTS valute (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency_code TEXT NOT NULL,  -- Код валюты (USD, CNY и т.д.)
            rate REAL NOT NULL,           -- Курс валюты
            date TEXT NOT NULL,           -- Дата изменения
            changes TEXT                  -- Описание изменений
        );''')

        # Таблица для хранения графиков курса юаня
        cursor.execute('''CREATE TABLE IF NOT EXISTS yuan_rate_graphs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            graph BLOB NOT NULL
        );''')

        conn.commit()

    # Создаем папки для хранения данных пользователей и валют
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs(VALUTE_DIR, exist_ok=True)



def save_user_history(user_id, calc_name, calc_type, result):
    """
    Сохраняет данные о расчете в файл и записывает его путь в базу данных.
    """
    user_folder = os.path.join(USERS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)  # Создаем папку пользователя, если её нет

    # Генерируем имя файла
    file_name = f"{calc_name}_{len(os.listdir(user_folder)) + 1}.json"
    file_path = os.path.join(user_folder, file_name)

    # Записываем расчет в JSON-файл
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"user_id": user_id, "calc_name": calc_name, "calc_type": calc_type, "result": result}, f, ensure_ascii=False, indent=4)

    # Записываем путь в базу данных
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO calculations (user_id, calc_name, calc_type, result, timestamp)
                          VALUES (?, ?, ?, ?, ?)''', 
                          (user_id, calc_name, calc_type, result, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()


def get_user_history(user_id):
    """
    Получает список расчетов пользователя.
    """
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT calc_name, calc_type, result, timestamp FROM calculations WHERE user_id = ?''', (user_id,))
        records = cursor.fetchall()

    # Загружаем данные из базы данных
    history = []
    for calc_name, calc_type, result, timestamp in records:
        history.append({
            "calc_name": calc_name,
            "calc_type": calc_type,
            "result": result,
            "timestamp": timestamp
        })

    return history


def save_valute_rate(currency_code, rate, changes):
    """
    Сохраняет курс валюты в базу данных.
    """
    date = datetime.today().strftime('%Y-%m-%d')

    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO valute (currency_code, rate, date, changes) 
                          VALUES (?, ?, ?, ?)''', (currency_code, rate, date, changes))
        conn.commit()


def get_valute_rate(currency_code):
    """
    Получает последний курс валюты из базы данных.
    """
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT rate FROM valute WHERE currency_code = ? 
                          ORDER BY date DESC LIMIT 1''', (currency_code,))
        result = cursor.fetchone()

    if result:
        return result[0]  # Возвращаем курс валюты
    else:
        return None  # Если данных нет, возвращаем None


def save_yuan_rate_graph(date, graph_data):
    """
    Сохраняет график курса юаня в таблицу.
    """
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO yuan_rate_graphs (date, graph) 
                          VALUES (?, ?)''', (date, graph_data))
        conn.commit()


def get_yuan_rate_graphs():
    """
    Получает все графики курса юаня.
    """
    with sqlite3.connect('database/bot_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM yuan_rate_graphs')
        graphs = cursor.fetchall()
    return graphs