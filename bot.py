import os
import time
import threading
import requests
import telebot
from flask import Flask, request
from datetime import datetime

TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
TWELVEDATA_API_KEY = 'e5626f0337684bb6b292e632d804029e'
CHAT_ID = 1671720900  # Твой Telegram ID для отправки сигналов

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

status = {'active': True}
last_signal = None

def get_candles(symbol='EUR/USD', interval='1min', outputsize=3):
    url = 'https://api.twelvedata.com/time_series'
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVEDATA_API_KEY,
        'format': 'JSON',
        'outputsize': outputsize
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if 'status' in data and data['status'] == 'error':
            if data.get('code') == 429:
                print("Лимит API превышен")
                return 'limit_exceeded'
            print("Ошибка API:", data)
            return None
        return data.get('values')
    except Exception as e:
        print("Ошибка при запросе котировок:", e)
        return None

def generate_signal(candles):
    if not candles or len(candles) < 3:
        return None
    close_0 = float(candles[0]['close'])
    close_1 = float(candles[1]['close'])
    close_2 = float(candles[2]['close'])
    diff1 = close_0 - close_1
    diff2 = close_1 - close_2
    if diff1 > 0 and diff2 > 0:
        return 'CALL'
    elif diff1 < 0 and diff2 < 0:
        return 'PUT'
    else:
        return None

def send_signal(signal):
    global last_signal
    if signal == last_signal:
        print("Сигнал такой же, не отправляем")
        return
    last_signal = signal
    text = f"📉 Сигнал по EUR/USD: {signal}\n🕐 Время: {datetime.utcnow().strftime('%H:%M:%S')} UTC"
    bot.send_message(CHAT_ID, text)
    print(f"Отправлен сигнал: {signal}")

def signal_loop():
    while True:
        if status['active']:
            candles = get_candles()
            if candles == 'limit_exceeded':
                time.sleep(3600)
                continue
            if candles:
                signal = generate_signal(candles)
                if signal:
                    send_signal(signal)
                else:
                    print("Сигнал не сгенерирован.")
            else:
                print("Данных нет.")
        else:
            print("Сигналы выключены.")
        time.sleep(60)

@app.route('/', methods=['GET'])
def set_webhook():
    host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if not host:
        return 'RENDER_EXTERNAL_HOSTNAME not set', 500
    webhook_url = f"https://{host}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'Webhook установлен по адресу: {webhook_url}', 200

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200

@bot.message_handler(commands=['start'])
def start_command(message):
    status['active'] = True
    bot.send_message(message.chat.id, "✅ Сигналы включены!")

@bot.message_handler(commands=['stop'])
def stop_command(message):
    status['active'] = False
    bot.send_message(message.chat.id, "🔴 Сигналы отключены!")

@bot.message_handler(commands=['status'])
def status_command(message):
    state = "включены" if status['active'] else "выключены"
    bot.send_message(message.chat.id, f"⚙️ Статус сигналов: {state}")

if __name__ == '__main__':
    threading.Thread(target=signal_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
