import os
import telebot
from flask import Flask, request

# Твой токен бота
TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
bot = telebot.TeleBot(TOKEN)

# Создаём Flask-приложение
app = Flask(__name__)

# Устанавливаем webhook
@app.route('/', methods=['GET'])
def set_webhook():
    host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if not host:
        return 'RENDER_EXTERNAL_HOSTNAME not set', 500

    webhook_url = f"https://{host}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'Webhook установлен по адресу: {webhook_url}', 200

# Обработка POST-запросов от Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)  # исправлено здесь
    bot.process_new_updates([update])
    return '', 200

# Простейший обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "✅ Бот успешно работает через Webhook!")

# Пример обработки текста
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    bot.send_message(message.chat.id, "Принято! Напиши /start для проверки.")

# Запуск приложения
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
