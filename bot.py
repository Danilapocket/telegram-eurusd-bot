import requests
import time
import telebot
import numpy as np
from datetime import datetime, timezone

# --- Настройки ---
API_KEY = "e5626f0337684bb6b292e632d804029e"  # Twelve Data API
TELEGRAM_TOKEN = "7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew"
USER_ID = 1671720900
INTERVAL = "1min"
LIMIT = 100

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_symbol_for_today():
    # weekday(): Пн=0, Вт=1, ..., Вс=6
    today = datetime.utcnow().weekday()
    if today >= 5:  # Суббота и Воскресенье
        return "EURUSD.OTC"  # Если не работает, попробуй "EURUSD.OCT"
    else:
        return "EUR/USD"

def get_price_data():
    symbol = get_symbol_for_today()
    print(f"[{datetime.now(timezone.utc)}] Используем символ: {symbol}")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&apikey={API_KEY}&outputsize={LIMIT}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        print("Ошибка получения данных:", data)
        return []

    closes = [float(x["close"]) for x in reversed(data["values"])]
    print(f"[{datetime.now(timezone.utc)}] Получено {len(closes)} закрытий")
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
        return None

    sma = sum(prices[-10:]) / 10
    rsi = calculate_rsi(prices, 14)
    price_now = prices[-1]

    print(f"[{datetime.now(timezone.utc)}] Цена: {price_now}, SMA: {sma}, RSI: {rsi}")

    if price_now > sma and rsi < 30:
        return "CALL", sma, rsi, price_now
    elif price_now < sma and rsi > 70:
        return "PUT", sma, rsi, price_now
    else:
        print(f"[{datetime.now(timezone.utc)}] Сигнал отсутствует")
        return None

def send_signal(direction, sma, rsi, price_now):
    time_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    emoji = "🟢" if direction == "CALL" else "🔴"

    message = f"""
📊 Сигнал по EUR/USD (1m)
🕒 Время: {time_now}
{emoji} {direction}

Цена: {price_now:.5f}
SMA(10): {sma:.5f}
RSI(14): {rsi}

⚠️ Это не инвестиционная рекомендация.
"""
    bot.send_message(USER_ID, message)

print("Бот запущен...")

while True:
    try:
        prices = get_price_data()
        if not prices:
            print("Нет данных, пропускаем цикл")
            time.sleep(60)
            continue
        result = get_signal(prices)
        if result:
            direction, sma, rsi, price_now = result
            send_signal(direction, sma, rsi, price_now)
        time.sleep(60)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(60)
