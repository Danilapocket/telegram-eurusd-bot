import time
import requests
import telebot
import logging
from datetime import datetime

# Твои ключи
TWELVEDATA_API_KEY = 'e5626f0337684bb6b292e632d804029e'
TELEGRAM_BOT_TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
TELEGRAM_CHAT_ID = 1671720900  # твой ID для отправки сообщений

# Инициализация бота Telegram
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

def get_candles(symbol='EURUSD.OTC', interval='1min', outputsize=20):
    url = f'https://api.twelvedata.com/time_series'
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVEDATA_API_KEY,
        'format': 'JSON',
        'outputsize': outputsize
    }
    response = requests.get(url, params=params)
    data = response.json()
    if 'status' in data and data['status'] == 'error':
        logging.error(f"Ошибка получения данных: {data}")
        return None
    return data.get('values')

def simple_strategy(candles):
    # Простая стратегия на основе последнего закрытия
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
    text = f"Сигнал на опционы: {signal} по EUR/USD"
    bot.send_message(TELEGRAM_CHAT_ID, text)
    logging.info(f"Отправлен сигнал: {signal}")

def main_loop():
    logging.info("Старт бота")
    while True:
        logging.info("Запрос данных для EURUSD.OTC")
        candles = get_candles()
        if candles is None:
            logging.info("Недостаточно данных для сигнала")
            time.sleep(60)
            continue

        signal = simple_strategy(candles)
        if signal:
            send_signal(signal)
        else:
            logging.info("Сигнал не получен, ждём следующей итерации.")

        time.sleep(60)  # Ожидаем 1 минуту до следующей итерации

if __name__ == '__main__':
    main_loop()
