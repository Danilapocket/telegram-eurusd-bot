import requests
import time
import telebot
import numpy as np
from datetime import datetime, timezone
import sys

LOGFILE = "bot.log"

def log(msg):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

log("Старт бота")

API_KEY = "e5626f0337684bb6b292e632d804029e"
TELEGRAM_TOKEN = "7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew"
USER_ID = 1671720900
INTERVAL = "1min"
LIMIT = 100

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_symbol_for_today():
    today = datetime.now(timezone.utc).weekday()
    if today >= 5:
        return "EURUSD.OTC"
    else:
        return "EUR/USD"

def get_price_data():
    symbol = get_symbol_for_today()
    log(f"Запрос данных для {symbol}")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&apikey={API_KEY}&outputsize={LIMIT}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        log(f"Ошибка получения данных: {data}")
        return []

    closes = [float(x["close"]) for x in reversed(data["values"])]
    log(f"Получено {len(closes)} закрытий. Пример последних: {closes[-5:]}")
    return closes

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = 100. - (100. / (1. + rs))

    for delta in deltas[period:]:
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi = 100. - (100. / (1. + rs))

    return round(rsi, 2)

def get_signal(prices):
    if len(prices) < 15:
        log("Недостаточно данных для сигнала")
        return None

    sma = sum(prices[-10:]) / 10
    rsi = calculate_rsi(prices, 14)
    price_now = prices[-1]

    log(f"Цена: {price_now:.5f}, SMA: {sma:.5f}, RSI: {rsi}")

    if price_now > sma and rsi < 50:
        log("Генерируем сигнал CALL")
        return "CALL", sma, rsi, price_now
    elif price_now < sma and rsi > 50:
        log("Генерируем сигнал PUT")
        return "PUT", sma, rsi, price_now
    else:
        log("Сигнал не сгенерирован")
        return None

def send_signal(direction, sma, rsi, price_now):
    time_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    emoji = "🟢" if direction == "CALL" else "🔴"

    message = f"""
📊 Сигнал по {get_symbol_for_today()} (1m)
🕒 Время: {time_now}
{emoji} {direction}

Цена: {price_now:.5f}
SMA(10): {sma:.5f}
RSI(14): {rsi}

⚠️ Это не инвестиционная рекомендация.
"""
    try:
        bot.send_message(USER_ID, message)
        log("Отправлено сообщение в Telegram")
    except Exception as e:
        log(f"Ошибка при отправке Telegram-сообщения: {e}")

log("Бот запущен...")

while True:
    try:
        log("Цикл итерация")
        prices = get_price_data()
        result = get_signal(prices)
        if result:
            direction, sma, rsi, price_now = result
            send_signal(direction, sma, rsi, price_now)
        else:
            log("Сигнал не получен, ждём следующей итерации.")
        time.sleep(10)
    except Exception as e:
        log(f"Ошибка в основном цикле: {e}")
        time.sleep(10)
