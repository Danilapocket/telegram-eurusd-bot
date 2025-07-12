import requests
import time
import telebot
import numpy as np
from datetime import datetime, timezone

# --- Настройки ---
API_KEY = "e5626f0337684bb6b292e632d804029e"
TELEGRAM_TOKEN = "7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew"
USER_ID = 1671720900
SYMBOL = "EUR/USD:FXCM"
INTERVAL = "1min"
LIMIT = 100

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_price_data():
    print(f"[{datetime.now(timezone.utc)}] Запрос данных с Twelve Data")
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={API_KEY}&outputsize={LIMIT}"
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
    up = deltas.clip(min=0)
    down = -deltas.clip(max=0)
    avg_gain = np.mean(up[:period])
    avg_loss = np.mean(down[:period])
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = [100 - 100 / (1 + rs)]
    for i in range(period, len(prices) - 1):
        avg_gain = (avg_gain * (period - 1) + up[i]) / period
        avg_loss = (avg_loss * (period - 1) + down[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi.append(100 - 100 / (1 + rs))
    return round(rsi[-1], 2)

def calculate_macd(prices, short=12, long=26, signal=9):
    ema_short = np.convolve(prices, np.ones(short)/short, mode='valid')
    ema_long = np.convolve(prices, np.ones(long)/long, mode='valid')
    macd_line = ema_short[-len(ema_long):] - ema_long
    signal_line = np.convolve(macd_line, np.ones(signal)/signal, mode='valid')
    return macd_line[-1], signal_line[-1]

def calculate_bollinger(prices, period=20):
    sma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    upper = sma + 2 * std
    lower = sma - 2 * std
    return round(upper, 5), round(lower, 5)

def get_signal(prices):
    if len(prices) < 30:
        return None

    rsi = calculate_rsi(prices)
    macd, macd_signal = calculate_macd(prices)
    upper_bb, lower_bb = calculate_bollinger(prices)
    ema10 = np.mean(prices[-10:])
    price_now = prices[-1]

    print(f"[{datetime.now(timezone.utc)}] Цена: {price_now:.5f}, RSI: {rsi}, EMA10: {ema10:.5f}, MACD: {macd:.5f}, Signal: {macd_signal:.5f}, BB_upper: {upper_bb}, BB_lower: {lower_bb}")

    if (price_now < lower_bb or price_now > ema10) and rsi < 40 and macd > macd_signal:
        return "CALL", rsi, macd, price_now
    elif (price_now > upper_bb or price_now < ema10) and rsi > 60 and macd < macd_signal:
        return "PUT", rsi, macd, price_now
    else:
        print(f"[{datetime.now(timezone.utc)}] Сигнал отсутствует")
        return None

def send_signal(direction, rsi, macd, price_now):
    time_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    emoji = "🟢" if direction == "CALL" else "🔴"
    message = f"""
📊 Сигнал по EUR/USD (1m)
🕒 Время: {time_now}
{emoji} {direction}

Цена: {price_now:.5f}
RSI(14): {rsi}
MACD: {macd:.5f}

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
            direction, rsi, macd, price_now = result
            send_signal(direction, rsi, macd, price_now)
        time.sleep(60)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(60)
