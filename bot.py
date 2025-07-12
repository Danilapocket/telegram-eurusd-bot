import requests
import time
import telebot
import numpy as np
from datetime import datetime, timezone

# --- Настройки ---
API_KEY = "e5626f0337684bb6b292e632d804029e"
TELEGRAM_TOKEN = "7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew"
USER_ID = 1671720900
SYMBOL = "EURUSD"
INTERVAL = "1min"
LIMIT = 100

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def log(msg: str):
    t = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{t}] {msg}")

def get_price_data():
    log("Запрос данных с Twelve Data")
    try:
        resp = requests.get(
            f"https://api.twelvedata.com/time_series", 
            params={"symbol": SYMBOL, "interval": INTERVAL, "apikey": API_KEY, "outputsize": LIMIT},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log(f"Ошибка запроса данных: {e}")
        return []

    if "values" not in data:
        log(f"Ошибка в ответе: {data}")
        return []

    closes = [float(x["close"]) for x in reversed(data["values"])]
    log(f"Получено {len(closes)} баров")
    return closes

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    up = deltas[:period][deltas[:period] >= 0].sum() / period
    down = -deltas[:period][deltas[:period] < 0].sum() / period
    rs = up/down if down else 0
    rsi = 100 - (100/(1+rs))
    up_avg, down_avg = up, down
    for delta in deltas[period:]:
        up_avg = (up_avg*(period-1) + max(delta,0))/period
        down_avg = (down_avg*(period-1) + -min(delta,0))/period
        rs = up_avg/down_avg if down_avg else 0
        rsi = round(100 - (100/(1+rs)), 2)
    return rsi

def get_signal(prices):
    if len(prices) < LIMIT:
        log("Недостаточно баров для сигнала")
        return None
    sma = sum(prices[-10:])/10
    rsi = calculate_rsi(prices, 14)
    price = prices[-1]
    log(f"Цена: {price:.5f}, SMA: {sma:.5f}, RSI: {rsi}")
    if price > sma and rsi < 30:
        return "CALL", sma, rsi, price
    if price < sma and rsi > 70:
        return "PUT", sma, rsi, price
    log("Сигнал отсутствует")
    return None

def send_signal(direction, sma, rsi, price):
    t = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    emoji = "🟢" if direction=="CALL" else "🔴"
    msg = f"""
📊 Сигнал по {SYMBOL} ({INTERVAL})
🕒 {t} — {emoji} {direction}
Цена: {price:.5f}
SMA(10): {sma:.5f}
RSI(14): {rsi}

⚠️ Это не инвестиционная рекомендация.
"""
    try:
        bot.send_message(USER_ID, msg)
        log("✅ Сигнал отправлен")
    except Exception as e:
        log(f"Ошибка отправки: {e}")

def main():
    log("Бот запущен")
    while True:
        try:
            prices = get_price_data()
            sig = get_signal(prices)
            if sig:
                send_signal(*sig)
            time.sleep(60)
        except Exception as e:
            log(f"⚠️ Ошибка RunLoop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
