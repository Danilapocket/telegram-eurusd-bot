import time
import requests
import telebot
import logging
from datetime import datetime

# --- Настройки ---
TWELVEDATA_API_KEY = 'e5626f0337684bb6b292e632d804029e'
TELEGRAM_BOT_TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
TELEGRAM_CHAT_ID = 1671720900  # ваш Telegram user ID

# --- Инициализация бота и логирования ---
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')


def get_candles(symbol='EURUSD.OTC', interval='1min', outputsize=20):
    url = 'https://api.twelvedata.com/time_series'
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVEDATA_API_KEY,
        'format': 'JSON',
        'outputsize': outputsize
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'status' in data and data['status'] == 'error':
            logging.error(f"Ошибка API: {data}")
            if data.get('code') == 429:
                return 'limit_exceeded'
            return None
        return data.get('values')
    except requests.RequestException as e:
        logging.error(f"Ошибка подключения к API: {e}")
        return None


def simple_strategy(candles):
    if not candles or len(candles) < 2:
        return None
    close_current = float(candles[0]['close'])
    close_prev = float(candles[1]['close'])

    if close_current > close_prev:
        return 'CALL'
    elif close_current < close_prev:
        return 'PUT'
    else:
        return None


def send_signal(signal):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"Сигнал на опционы: {signal} по EUR/USD\nВремя: {now}"
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text)
        logging.info(f"Отправлен сигнал: {signal} ({now})")
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения: {e}")


def main_loop():
    logging.info("Бот запущен")
    last_signal = None

    while True:
        current_day = datetime.now().weekday()  # 0 = Пн, 6 = Вс
        if current_day >= 5:  # Суббота и воскресенье
            logging.info("Выходной день. Бот спит 1 минуту.")
            time.sleep(60)
            continue

        logging.info("Получение данных EURUSD.OTC...")
        candles = get_candles()

        if candles == 'limit_exceeded':
            logging.error("Превышен лимит API. Пауза на 1 час.")
            time.sleep(3600)
            continue

        if candles is None:
            logging.info("Ошибка получения данных. Повтор через 1 минуту.")
            time.sleep(60)
            continue

        signal = simple_strategy(candles)
        if signal and signal != last_signal:
            send_signal(signal)
            last_signal = signal
        else:
            logging.info("Сигнал не получен или не изменился.")

        time.sleep(60)


if __name__ == '__main__':
    main_loop()
