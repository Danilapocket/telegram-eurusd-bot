import asyncio
import json
import numpy as np
import telebot
from datetime import datetime, timezone
import websockets

# --- Настройки ---
TELEGRAM_TOKEN = "7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew"
USER_ID = 1671720900
SYMBOL = "FX:EURUSD"  # TradingView формат для OTC EUR/USD
INTERVAL = "1"  # 1 минута

bot = telebot.TeleBot(TELEGRAM_TOKEN)


def calculate_sma(prices, period=10):
    if len(prices) < period:
        return None
    return np.mean(prices[-period:])


def calculate_rsi(prices, period=14):
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


def calculate_bollinger_bands(prices, period=20, std_dev_factor=2):
    if len(prices) < period:
        return None, None
    sma = np.mean(prices[-period:])
    std_dev = np.std(prices[-period:])
    upper_band = sma + std_dev_factor * std_dev
    lower_band = sma - std_dev_factor * std_dev
    return upper_band, lower_band


def calculate_macd(prices, slow=26, fast=12, signal=9):
    if len(prices) < slow + signal:
        return None, None, None
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line[-signal:], signal)
    histogram = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], histogram


def ema(prices, period):
    ema_values = []
    k = 2 / (period + 1)
    for i, price in enumerate(prices):
        if i == 0:
            ema_values.append(price)
        else:
            ema_values.append(price * k + ema_values[-1] * (1 - k))
    return np.array(ema_values)


def generate_signal(prices):
    if len(prices) < 30:
        return None

    price_now = prices[-1]
    sma = calculate_sma(prices, 10)
    rsi = calculate_rsi(prices, 14)
    upper_band, lower_band = calculate_bollinger_bands(prices, 20)
    macd_line, signal_line, histogram = calculate_macd(prices)

    print(f"[{datetime.now(timezone.utc)}] price={price_now:.5f}, SMA={sma:.5f}, RSI={rsi}, BB_up={upper_band:.5f}, BB_low={lower_band:.5f}, MACD={macd_line:.5f}, Signal={signal_line:.5f}, Hist={histogram:.5f}")

    # Простая логика сигналов:
    # CALL: Цена выше SMA, RSI < 30, MACD гистограмма растет, цена ниже нижней BB (перепроданность)
    # PUT: Цена ниже SMA, RSI > 70, MACD гистограмма падает, цена выше верхней BB (перекупленность)

    if price_now > sma and rsi is not None and rsi < 30 and histogram > 0 and price_now < lower_band:
        return "CALL", sma, rsi, price_now
    elif price_now < sma and rsi is not None and rsi > 70 and histogram < 0 and price_now > upper_band:
        return "PUT", sma, rsi, price_now
    else:
        return None


def send_signal(direction, sma, rsi, price_now):
    time_now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    emoji = "🟢" if direction == "CALL" else "🔴"
    message = f"""
📊 Сигнал по {SYMBOL} (1m)
🕒 Время: {time_now}
{emoji} {direction}

Цена: {price_now:.5f}
SMA(10): {sma:.5f}
RSI(14): {rsi}

⚠️ Это не инвестиционная рекомендация.
"""
    bot.send_message(USER_ID, message)


async def tradingview_ws():
    url = "wss://data.tradingview.com/socket.io/websocket"
    prices = []

    async with websockets.connect(url) as ws:
        # Подписка на нужный тикер и интервал
        # Формат сообщений и подписки можно найти в open source TradingView WS clients

        # Пример подписки, нужно адаптировать под TradingView protocol
        # Для простоты - сюда нужно добавить реальный подписочный JSON

        # TODO: Подписка на EURUSD с 1m интервалом
        # Если потребуется, могу помочь с точной подпиской.

        # Для примера: будем эмулировать получение цен
        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            # Обработка данных: нужно вытащить цену закрытия свечи из data
            # Добавим цену в prices, удерживая последние 100 значений
            # prices.append(close_price)
            # if len(prices) > 100:
            #     prices.pop(0)

            # Потом генерируем сигнал
            signal = generate_signal(prices)
            if signal:
                direction, sma, rsi, price_now = signal
                send_signal(direction, sma, rsi, price_now)

            await asyncio.sleep(60)


if __name__ == "__main__":
    print("Бот запущен...")

    # Запускаем Telegram polling параллельно
    import threading

    def telegram_polling():
        bot.infinity_polling()

    threading.Thread(target=telegram_polling, daemon=True).start()

    # Запускаем asyncio event loop для WS
    asyncio.run(tradingview_ws())
