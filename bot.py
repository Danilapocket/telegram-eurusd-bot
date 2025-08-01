import time
import requests
import telebot
import logging
from datetime import datetime, timedelta
import pytz

# Токены
TWELVEDATA_API_KEY = 'e5626f0337684bb6b292e632d804029e'
TELEGRAM_BOT_TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
TELEGRAM_CHAT_ID = 1671720900

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

signals_enabled = True
stats = {'CALL': 0, 'PUT': 0, 'total': 0}
last_signal = None
last_candle_time = None

moscow_tz = pytz.timezone("Europe/Moscow")

def in_working_hours():
    now = datetime.now(moscow_tz).hour
    return 8 <= now < 24

def fetch_candles():
    try:
        resp = requests.get('https://api.twelvedata.com/time_series', params={
            'symbol': 'EUR/USD',
            'interval': '1min',
            'apikey': TWELVEDATA_API_KEY,
            'format': 'JSON',
            'outputsize': 3
        }, timeout=10)
        data = resp.json()
        if data.get('status') == 'error':
            if data.get('code') == 429:
                return 'limit'
            return None
        return data.get('values')
    except Exception as e:
        logging.error("Error fetching candles: %s", e)
        return None

def generate_signal(candles):
    if not candles or len(candles) < 3:
        return None
    diff1 = float(candles[0]['close']) - float(candles[1]['close'])
    diff2 = float(candles[1]['close']) - float(candles[2]['close'])
    if diff1 > 0 and diff2 > 0:
        return 'CALL'
    if diff1 < 0 and diff2 < 0:
        return 'PUT'
    return None

def send_signal(sig):
    global last_signal
    if sig == last_signal:
        return
    last_signal = sig
    stats[sig] += 1
    stats['total'] += 1
    now = datetime.now(moscow_tz).strftime('%H:%M:%S')
    emoji = "🟢" if sig == 'CALL' else "🔴"
    text = (f"{emoji} Сигнал по EUR/USD: <b>{sig}</b>\n"
            f"🕒 Время: {now} UTC+3")
    bot.send_message(TELEGRAM_CHAT_ID, text, parse_mode='HTML')
    logging.info("Sent %s at %s", sig, now)

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    global signals_enabled
    signals_enabled = True
    bot.send_message(msg.chat.id, "🟢 Сигналы включены")

@bot.message_handler(commands=['stop'])
def cmd_stop(msg):
    global signals_enabled
    signals_enabled = False
    bot.send_message(msg.chat.id, "🔴 Сигналы отключены")

@bot.message_handler(commands=['status'])
def cmd_status(msg):
    bot.send_message(msg.chat.id,
                     "⚙️ Сигналы " + ("включены" if signals_enabled else "отключены"))

@bot.message_handler(commands=['stats'])
def cmd_stats(msg):
    bot.send_message(msg.chat.id,
                     f"📊 СТАТИСТИКА\nCALL: {stats['CALL']}\nPUT: {stats['PUT']}\nВсего: {stats['total']}")

def loop():
    global last_candle_time
    logging.info("Signal loop started")
    while True:
        if not signals_enabled or not in_working_hours():
            time.sleep(5)
            continue

        candles = fetch_candles()
        if candles == 'limit':
            logging.warning("API limit reached, pausing 1h")
            time.sleep(3600)
            continue
        if not candles:
            time.sleep(10)
            continue

        ct = candles[0]['datetime']
        if ct == last_candle_time:
            time.sleep(5)
            continue
        last_candle_time = ct
        sig = generate_signal(candles)
        if sig:
            # отправляем с небольшой задержкой
            time.sleep(5)
            send_signal(sig)
        time.sleep(5)

if __name__ == '__main__':
    import threading
    threading.Thread(target=loop, daemon=True).start()
    bot.polling(none_stop=True)
