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
    # weekday(): Пн=0, ..., Вс=6
    today = datetime.now(timezone.utc).weekday()
    if today >= 5:  # Сб, Вс — выходные
        return "EUR/USD-OTC"
    else:
        return "EUR/USD"


def get_price_data():
    symbol = get_symbol_for_today()
    print(f"[{datetime.now(timezone.utc)}] Запрос данных для символа {symbol} с Twelve Data")
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


def calculate_ema(prices, period=10):
    prices = np.array(prices)
    ema = [np.mean(prices[:period])]
    k = 2 / (period + 1)
    for price in prices[period:]:
        ema.append((price - ema[-1]) * k + ema[-1])
    return ema[-1]


def get_signal(prices):
    if len(prices) < 20:
        return None

    sma = sum(prices[-10:]) / 10
    ema = calculate_ema(prices[-20:], 10)
    rsi = calculate_rsi(prices, 14)
    price_now = prices[-1]

    print(f"[{datetime.now(timezone.utc)}] Цена: {price_now}, SMA: {sma}, EMA: {ema:.5f}, RSI: {rsi}")

    # Пример условия для сигнала с EMA + SMA + RSI
    if price_now > sma and price_now > ema and rsi < 30:
        return "CALL", sma, ema, rsi, price_now
    elif price_now < sma and price_now < ema and rsi > 70:
        return "PUT", sma, ema, rsi, price_now
    else:
        print(f"[{datetime.now(timezone.utc)}] Сигнал отсутствует")
        return None


def send_signal(direction, sma, ema, rsi, price_now):
    time_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    emoji = "🟢" if direction == "CALL" else "🔴"

    message = f"""
📊 Сигнал по {get_symbol_for_today()} (1m)
🕒 Время: {time_now}
{emoji} {direction}

Цена: {price_now:.5f}
SMA(10): {sma:.5f}
EMA(10): {ema:.5f}
RSI(14): {rsi}

⚠️ Это не инвестиционная рекомендация.
"""
    bot.send_message(USER_ID, message)


# --- Основной цикл ---
print("Бот запущен...")
while True:
    try:
        prices = get_price_data()
        result = get_signal(prices)
        if result:
            direction, sma, ema, rsi, price_now = result
            send_signal(direction, sma, ema, rsi, price_now)
        time.sleep(60)  # Ждём 1 минуту
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(60)
