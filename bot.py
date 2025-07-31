import telebot
import pytz
from datetime import datetime, timedelta
import threading
import time

TOKEN = 'твой_токен'
bot = telebot.TeleBot(TOKEN)

running = True

def get_signal():
    # Тут твоя логика генерации сигнала
    import random
    direction = random.choice(["CALL", "PUT"])

    # Текущее время UTC+3 с округлением до следующей минуты
    tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(tz) + timedelta(seconds=20)
    signal_time = now.replace(second=0, microsecond=0)
    signal_str = signal_time.strftime("%H:%M:%S")

    return direction, signal_str

def send_signal():
    direction, signal_time = get_signal()
    msg = f"📉 Сигнал по EUR/USD: {direction}\n🕒 Время: {signal_time} UTC+3"
    bot.send_message(chat_id='@твоя_группа_или_id', text=msg)

def main_loop():
    global running
    while running:
        now = datetime.utcnow()
        if now.second == 40:  # отправка сигнала за 20 сек до новой минуты
            send_signal()
            time.sleep(1)
        time.sleep(0.5)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Бот запущен!")

@bot.message_handler(commands=['stop'])
def stop(message):
    global running
    running = False
    bot.send_message(message.chat.id, "Бот остановлен!")

@bot.message_handler(commands=['status'])
def status(message):
    bot.send_message(message.chat.id, f"Бот активен: {running}")

@bot.message_handler(commands=['stats'])
def stats(message):
    bot.send_message(message.chat.id, "Статистика пока недоступна.")

if __name__ == '__main__':
    import threading
    threading.Thread(target=main_loop).start()
    bot.remove_webhook()
    bot.polling(none_stop=True)
