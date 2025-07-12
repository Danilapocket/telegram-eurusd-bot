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

def get_symbol():
    # На выходных — OTC, в будни — обычный EUR/USD
    today = datetime.now(timezone.utc).weekday()
    if today >= 5:
        return "EURUSD.OTC"
    else:
        return "EUR/USD"

def get_price_data():
    symbol = get_symbol()
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&apikey={API_KEY}&outputsize={LIMIT}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        print(f"[{datetime.now(timezone.utc)}] Ошибка получения данных:", data)
        return []

    closes = [float(x["close"]) for x in reversed(data["values"])]
    return closes

def SMA(prices, period=10):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def RSI(prices, period=14):
    if len(prices) < period + 1:
        return None
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

def BollingerBands(prices, period=20, std_dev=2):
    if len(prices) < period:
        return None, None, None
    sma = SMA(prices, period)
    std = np.std(prices[-period:])
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return lower, sma, upper

def MACD(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal:
        return None, None, None
    ema_fast = EMA(prices, fast)
    ema_slow = EMA(prices, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = np.array(ema_fast) - np.array(ema_slow)
    signal_line = EMA(macd_line.tolist(), signal)
    histogram = macd_line[-1] - signal_line[-1] if signal_line else None
    return macd_line[-1], signal_line[-1], histogram

def EMA(prices, period):
    if len(prices) < period:
        return None
    prices = np.array(prices)
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    a = np.convolve(prices, weights, mode='valid')
    return a.tolist()

def get_signal(prices):
    if len(prices) < 30:
        return None

    sma_10 = SMA(prices, 10)
    rsi_14 = RSI(prices, 14)
    bb_lower, bb_middle, bb_upper = BollingerBands(prices, 20, 2)
    macd_line, signal_line, macd_hist = MACD(prices)

    price_now = prices[-1]

    # Логика сигналов — комбинированная:
    # CALL — цена выше SMA, RSI < 30 (перепродан), цена около нижней полосы Боллинджера,
    # и MACD пересекает сигнал снизу вверх
    # PUT — цена ниже SMA, RSI > 70 (перекуплен), цена около верхней полосы Боллинджера,
    # и MACD пересекает сигнал сверху вниз

    call_condition = (
        price_now > sma_10 and
        rsi_14 < 30 and
        price_now < bb_lower * 1.01 and
        macd_hist is not None and macd_hist > 0
    )

    put_condition = (
        price_now < sma_10 and
        rsi_14 > 70 and
        price_now > bb_upper * 0.99 and
        macd_hist is not None and macd_hist < 0
    )

    print(f"[{datetime.now(timezone.utc)}] price={price_now:.5f} SMA={sma_10:.5f} RSI={rsi_14} BB_lower={bb_lower:.5f} BB_upper={bb_upper:.5f} MACD_hist={macd_hist}")

    if call_condition:
        return "CALL", sma_10, rsi_14, price_now
    elif put_condition:
        return "PUT", sma_10, rsi_14, price_now
    else:
        return None

def send_signal(direction, sma, rsi, price_now):
    time_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    emoji = "🟢" if direction == "CALL" else "🔴"
    symbol = get_symbol()

    message = (
        f"📊 Сигнал по {symbol} (1m)\n"
        f"🕒 Время: {time_now}\n"
        f"{emoji} {direction}\n\n"
        f"Цена: {price_now:.5f}\n"
        f"SMA(10): {sma:.5f}\n"
        f"RSI(14): {rsi}\n\n"
        "⚠️ Это не инвестиционная рекомендация."
    )
    bot.send_message(USER_ID, message)

print("Бот запущен...")

while True:
    try:
        prices = get_price_data()
        signal = get_signal(prices)
        if signal:
            direction, sma, rsi, price_now = signal
            send_signal(direction, sma, rsi, price_now)
        else:
            print(f"[{datetime.now(timezone.utc)}] Сигнал отсутствует")
        time.sleep(60)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(60)
