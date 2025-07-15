import time
import requests
import telebot
import logging
from datetime import datetime
from telebot import types

# --- Конфигурация ---
API_KEY = 'e5626f0337684bb6b292e632d804029e'
BOT_TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
CHAT_ID = 1671720900

bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# --- Глобальные переменные ---
last_signal = None
signals_enabled = True
last_market_closed = False
stats = {"CALL": 0, "PUT": 0, "total": 0}

# --- Telegram кнопки ---
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
markup.row('/start', '/stop')
markup.row('/stats', '/status')

# --- Получение данных с индикаторами ---
def get_indicators():
    url = 'https://api.twelvedata.com/time_series'
    params = {
        'symbol': 'EUR/USD',
        'interval': '1min',
        'outputsize': 50,
        'apikey': API_KEY,
        'indicators': 'rsi,macd,sma,ema,bbands'
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'values' not in data:
            return None
        return data['values']
    except Exception as e:
        logging.error(f"Ошибка получения данных: {e}")
        return None

# --- Простая фильтр-стратегия на основе нескольких индикаторов ---
def generate_signal(data):
    if not data or len(data) < 2:
        return None

    try:
        last = data[0]
        prev = data[1]

        close_now = float(last['close'])
        close_prev = float(prev['close'])

        rsi = float(last.get('rsi', 0))
        macd = float(last.get('macd', 0))
        sma = float(last.get('sma', 0))
        ema = float(last.get('ema', 0))
        upper_bb = float(last.get('bbands_upper', 0))
        lower_bb = float(last.get('bbands_lower', 0))

        # Пример логики:
        if close_now > sma and close_now > ema and rsi > 50 and macd > 0 and close_now < upper_bb:
            return 'CALL'
        elif close_now < sma and close_now < ema and rsi < 50 and macd < 0 and close_now > lower_bb:
            return 'PUT'
        else:
            return None
    except Exception as e:
        logging.error(f"Ошибка в стратегии: {e}")
        return None

# --- Отправка сигнала ---
def send_signal(signal):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"📉 Сигнал по EUR/USD: *{signal}*\n🕐 Время: `{now}`"
    bot.send_message(CHAT_ID, text, parse_mode='Markdown')
    logging.info(f"Отправлен сигнал: {signal}")
    stats[signal] += 1
    stats["total"] += 1

# --- Основной цикл ---
def main_loop():
    global last_signal, signals_enabled, last_market_closed

    logging.info("Бот запущен.")
    while True:
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour

        if weekday >= 5 or hour < 7 or hour >= 21:
            if not last_market_closed:
                bot.send_message(CHAT_ID, "❌ Рынок закрыт. Бот приостановлен.", reply_markup=markup)
                last_market_closed = True
            time.sleep(60)
            continue
        else:
            if last_market_closed:
                bot.send_message(CHAT_ID, "✅ Рынок открыт. Бот возобновил работу.", reply_markup=markup)
                last_market_closed = False

        if not signals_enabled:
            time.sleep(10)
            continue

        data = get_indicators()
        signal = generate_signal(data)

        if signal and signal != last_signal:
            send_signal(signal)
            last_signal = signal
        else:
            logging.info("Новый сигнал не сгенерирован или повтор предыдущего.")

        time.sleep(60)

# --- Команды Telegram ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    global signals_enabled
    signals_enabled = True
    bot.send_message(message.chat.id, "🟢 Сигналы включены", reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    global signals_enabled
    signals_enabled = False
    bot.send_message(message.chat.id, "🔴 Сигналы отключены", reply_markup=markup)

@bot.message_handler(commands=['status'])
def status_cmd(message):
    status = "🟢 ВКЛЮЧЕН" if signals_enabled else "🔴 ВЫКЛЮЧЕН"
    bot.send_message(message.chat.id, f"📡 Статус сигналов: {status}", reply_markup=markup)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    summary = f"""📊 Статистика:
CALL: {stats['CALL']}
PUT: {stats['PUT']}
Всего: {stats['total']}
"""
    bot.send_message(message.chat.id, summary, reply_markup=markup)

# --- Запуск бота и цикла ---
if __name__ == '__main__':
    import threading
    threading.Thread(target=main_loop).start()
    bot.infinity_polling()
