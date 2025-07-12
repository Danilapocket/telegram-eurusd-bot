import asyncio
import json
import numpy as np
import telebot
from datetime import datetime, timezone
import websockets
import threading

# === Настройки ===
TELEGRAM_TOKEN = "7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew"
USER_ID = 1671720900

SYMBOL = "FX:EURUSD"  # Символ TradingView для EUR/USD OTC
INTERVAL = "1"  # 1-минутный таймфрейм

bot = telebot.TeleBot(TELEGRAM_TOKEN)
prices = []  # Хранение последних цен закрытия (close)


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


def generate_signal(prices):
    if len(prices) < 15:
        return None

    price_now = prices[-1]
    sma = calculate_sma(prices, 10)
    rsi = calculate_rsi(prices, 14)

    print(f"[{datetime.now(timezone.utc)}] Цена: {price_now:.5f}, SMA: {sma:.5f}, RSI: {rsi}")

    if price_now > sma and rsi is not None and rsi < 30:
        return "CALL", sma, rsi, price_now
    elif price_now < sma and rsi is not None and rsi > 70:
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
    global prices
    url = "wss://data.tradingview.com/socket.io/websocket"

    async with websockets.connect(url) as ws:
        # Инициализация сессии
        await ws.send('~m~8~m~{"session_id":"","timestamp":0}')
        await asyncio.sleep(1)

        # Создаем сессию для запроса котировок
        await ws.send(f'~m~{len(json.dumps({"m":"quote_create_session","p":["qs_1", SYMBOL]}))}~m~{json.dumps({"m":"quote_create_session","p":["qs_1", SYMBOL]})}')
        await asyncio.sleep(1)

        # Подписываемся на данные 1м таймфрейма
        await ws.send(f'~m~{len(json.dumps({"m":"resolve_symbol","p":["qs_1", SYMBOL]}))}~m~{json.dumps({"m":"resolve_symbol","p":["qs_1", SYMBOL]})}')
        await asyncio.sleep(1)

        await ws.send(f'~m~{len(json.dumps({"m":"create_series","p":["qs_1", "s1", "1", "1"]}))}~m~{json.dumps({"m":"create_series","p":["qs_1", "s1", INTERVAL, "1"]})}')
        await asyncio.sleep(1)

        while True:
            try:
                msg = await ws.recv()
                if msg.startswith("~m~"):
                    msg_json = msg[msg.find("{"):]
                    data = json.loads(msg_json)

                    # Обрабатываем новые бары
                    if data.get("m") == "timescale_update":
                        bars = data.get("p", [])[1].get("bars", [])
                        for bar in bars:
                            close_price = bar["close"]
                            if len(prices) == 0 or prices[-1] != close_price:
                                prices.append(close_price)
                                if len(prices) > 100:
                                    prices.pop(0)
                                signal = generate_signal(prices)
                                if signal:
                                    direction, sma, rsi, price_now = signal
                                    send_signal(direction, sma, rsi, price_now)

            except Exception as e:
                print("Ошибка WebSocket:", e)
                await asyncio.sleep(5)


def start_telegram_polling():
    bot.infinity_polling()


if __name__ == "__main__":
    print("Бот запущен...")

    # Запускаем Telegram polling в отдельном потоке
    threading.Thread(target=start_telegram_polling, daemon=True).start()

    # Запускаем WebSocket клиент
    asyncio.run(tradingview_ws())
