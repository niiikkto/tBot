import telebot
#from telebot import TeleBot
from telebot import types
import sqlite3

import requests
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Подключение к базе данных (файл будет создан, если не существует)
    conn = sqlite3.connect('db/database.db', check_same_thread=False)
    cursor = conn.cursor()

    # Создание таблицы (в SQLite INTEGER PRIMARY KEY работает как auto_increment)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT, 
                user_name TEXT)''')
    
    # Создание таблицы (в SQLite INTEGER PRIMARY KEY работает как auto_increment)
    cursor.execute('''CREATE TABLE IF NOT EXISTS api
               (Api_key VARCHAR)''')

    # Сохранение изменений
    conn.commit()

    # Закрытие соединения
    cursor.close()
    conn.close()

    bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}! \nДавай зарегистрируемся. \nВведите имя:")
    bot.register_next_step_handler(message, name)

def name(message):
    user_data[message.chat.id] = {'name': message.text.strip()}
    user_data[message.chat.id]['user_name'] = message.from_user.username
    name = user_data[message.chat.id]['name']
    username = user_data[message.chat.id]['user_name']

    conn = sqlite3.connect('db/database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (name, user_name) VALUES (?, ?)', (name, username))
    conn.commit()
    cursor.close()
    conn.close()

    print(f"Добавлен пользователь: {name}, {username}")
    bot.send_message(message.chat.id, "Пользователь зарегистрирован!")

    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton('Помощь')
    markup.row(btn1)
    btn2 = types.KeyboardButton('Поиск фильмов')
    btn3 = types.KeyboardButton('Поиск игр')
    btn4 = types.KeyboardButton('Поиск книг')
    markup.row(btn2, btn3, btn4)
    welcome_text = f"Привет, {message.from_user.first_name}! Я бот с искусственным интеллектом.👾 \nДля подборки 🎥фильмов, 🎮игр и 📚книг. По ключевым словам!"
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    bot.register_next_step_handler(message, on_click)

@bot.message_handler()
def on_click(message):
    #Поиск фильмов
    if message.text == 'Поиск фильмов':
        movies_text = "🎥Введите несколько ключевых слов, чтобы я мог порекомендывать вам фильм на вечер!"
        bot.send_message(message.chat.id, movies_text)
        bot.register_next_step_handler(message, lambda msg: handle_query(msg, message.text))
    #Поиск игр
    elif message.text == 'Поиск игр':
        games_text = "🎮Введите несколько ключевых слов, чтобы я мог порекомендывать вам увлекательную игру!"
        bot.send_message(message.chat.id, games_text)
        bot.register_next_step_handler(message, lambda msg: handle_query(msg, message.text))
    #Поиск книг
    elif message.text == 'Поиск книг':
        books_text = "📚Введите несколько ключевых слов, чтобы я мог порекомендывать вам интересную книгу для прочтения!"
        bot.send_message(message.chat.id, books_text)
        bot.register_next_step_handler(message, lambda msg: handle_query(msg, message.text))
    #Помощь
    else:
        help_text = "Я бот с искусственным интеллектом.👾 \nДля подборки фильмов, игр и книг. По ключевым словам! \nИспользуй кнопки для поиска 🎥фильмов, 🎮игр или 📚книг по ключевым словам."
        bot.send_message(message.chat.id, help_text)

def handle_query(message, query_type):
    try:
        # Показываем статус "печатает"
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Формируем промпт в зависимости от типа запроса
        if query_type == 'Поиск фильмов':
            prompt = f"Рекомендуй фильм по следующим ключевым словам: {message.text} сделай формат текста без символов"
        elif query_type == 'Поиск игр':
            prompt = f"Рекомендуй игру по следующим ключевым словам: {message.text} сделай формат текста без символов"
        elif query_type == 'Поиск книг':
            prompt = f"Рекомендуй книгу по следующим ключевым словам: {message.text}  сделай формат текста без символов"
        else:
            prompt = message.text
            
        # Получаем ответ от GPT
        response = query_openrouter(prompt)
        
        # Отправляем ответ пользователю
        bot.reply_to(message, response)
    except Exception as e:
        print(f"Ошибка при обработке сообщения: {e}")
        bot.reply_to(message, "Извините, произошла ошибка. Пожалуйста, попробуйте позже.")

def query_openrouter(prompt):
    """
    Отправляет запрос к OpenRouter API и возвращает ответ
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
            {"role": "system", "content": "Вы - полезный ассистент, который отвечает на вопросы пользователя. Отвечайте кратко и по существу."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Ошибка при запросе к OpenRouter API: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."

print('Бот запущен!')
print(os.path.abspath('db/database.db'))
bot.polling(none_stop=True)