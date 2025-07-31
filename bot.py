import time
import requests
import telebot
import logging
from datetime import datetime, timezone, timedelta

# Токены
TWELVEDATA_API_KEY = 'e5626f0337684bb6b292e632d804029e'
TELEGRAM_BOT_TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
TELEGRAM_CHAT_ID = 1671720900

# Настройки
DAY_START = 9   # начало рабочего времени UTC+3
DAY_END = 22    # конец рабочего времени UTC+3
ADVANCE_SECONDS = 20  # сколько заранее отправляем сигнал

# Telegram-бот
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Логирование
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

status = {'active': True}
stats = {'CALL': 0, 'PUT': 0, 'total': 0}
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
        if data.get('status') == 'error':
            logging.error(f"Ошибка API: {data}")
            if data.get('code') == 429:
                return 'limit_exceeded'
            return None
        return data.get('values')
    except Exception as e:
        logging.error(f"Ошибка при запросе котировок: {e}")
        return None

def generate_signal(candles):
    if not candles or len(candles) < 3:
        return None
    close0 = float(candles[0]['close'])
    close1 = float(candles[1]['close'])
    close2 = float(candles[2]['close'])
    if close0 > close1 > close2:
        return 'CALL'
    if close0 < close1 < close2:
        return 'PUT'
    return None

def send_signal(signal):
    global last_signal
    if signal == last_signal:
        return
    last_signal = signal
    stats[signal] += 1
    stats['total'] += 1

    tz = timezone(timedelta(hours=3))
    now = datetime.now(tz).strftime('%H:%M:%S')
    msg = f"📉 Сигнал по EUR/USD: {signal}\n🕒 Время (UTC+3): {now}"
    bot.send_message(TELEGRAM_CHAT_ID, msg)
    logging.info(f"Отправлен сигнал: {signal} ({now} UTC+3)")

def main_loop():
    logging.info("Бот запущен.")
    tz = timezone(timedelta(hours=3))
    while True:
        if not status['active']:
            time.sleep(5); continue

        now = datetime.now(tz)
        hour = now.hour
        second = now.second

        # В рабочее время?
        if not (DAY_START <= hour < DAY_END):
            time.sleep(60); continue

        if second >= 60 - ADVANCE_SECONDS:
            candles = get_candles()
            if candles == 'limit_exceeded':
                logging.warning("Превышен лимит API. Ждём 1 час.")
                time.sleep(3600); continue
            if not candles:
                time.sleep(60); continue

            signal = generate_signal(candles)
            if signal:
                send_signal(signal)

            # Ждём переход в следующую минуту
            time.sleep(60 - second)
        else:
            time.sleep(0.5)

@bot.message_handler(commands=['start'])
def handle_start(msg):
    status['active'] = True
    bot.send_message(msg.chat.id, "🟢 Сигналы включены")

@bot.message_handler(commands=['stop'])
def handle_stop(msg):
    status['active'] = False
    bot.send_message(msg.chat.id, "🔴 Сигналы отключены")

@bot.message_handler(commands=['status'])
def handle_status(msg):
    state = "включены" if status['active'] else "отключены"
    bot.send_message(msg.chat.id, f"⚙️ Сигналы {state}")

@bot.message_handler(commands=['stats'])
def handle_stats(msg):
    bot.send_message(
        msg.chat.id,
        f"📊 Статистика:\nCALL: {stats['CALL']}\nPUT: {stats['PUT']}\nВсего: {stats['total']}"
    )

if __name__ == '__main__':
    import threading
    threading.Thread(target=main_loop, daemon=True).start()
    bot.remove_webhook()
    bot.polling(none_stop=True)
