import time
import requests
import telebot
import logging
from datetime import datetime, timedelta

# Токены
TWELVEDATA_API_KEY = 'e5626f0337684bb6b292e632d804029e'
TELEGRAM_BOT_TOKEN = '7566716689:AAGqf-h68P2icgJ0T4IySEhwnEvqtO81Xew'
TELEGRAM_CHAT_ID = 1671720900

# Telegram-бот
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Логирование
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# Статус и статистика
status = {'active': True}
stats = {'CALL': 0, 'PUT': 0, 'total': 0}
last_signal = None

# Получение котировок
def get_candles(symbol='EUR/USD', interval='1min', outputsize=3):
    url = 'https://api.twelvedata.com/time_series'
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': TWELVEDATA_API_KEY,
        'format': 'JSON',
        'outputsize': outputsize
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if 'status' in data and data['status'] == 'error':
            logging.error(f"Ошибка API: {data}")
            if data['code'] == 429:
                return 'limit_exceeded'
            return None
        return data.get('values')
    except Exception as e:
        logging.error(f"Ошибка при запросе котировок: {e}")
        return None

# Более чувствительная стратегия
def generate_signal(candles):
    if not candles or len(candles) < 3:
        return None

    close_0 = float(candles[0]['close'])
    close_1 = float(candles[1]['close'])
    close_2 = float(candles[2]['close'])

    diff1 = close_0 - close_1
    diff2 = close_1 - close_2

    if diff1 > 0 and diff2 > 0:
        return 'CALL'
    elif diff1 < 0 and diff2 < 0:
        return 'PUT'
    else:
        return None

# Проверка времени по UTC+3
def is_active_hours():
    utc_plus_3 = datetime.utcnow() + timedelta(hours=3)
    current_hour = utc_plus_3.hour
    return 8 <= current_hour < 24

# Отправка сигнала в Telegram
def send_signal(signal):
    global last_signal
    if signal == last_signal:
        logging.info("Новый сигнал не сгенерирован или повтор предыдущего.")
        return
    last_signal = signal
    stats[signal] += 1
    stats['total'] += 1

    utc_plus_3 = datetime.utcnow() + timedelta(hours=3)
    local_time = utc_plus_3.strftime('%H:%M:%S')

    color = "🟢" if signal == "CALL" else "🔴"
    text = (
        f"{color} Сигнал по EUR/USD: {signal}\n"
        f"🕐 Время: {local_time} UTC+3"
    )
    bot.send_message(TELEGRAM_CHAT_ID, text)
    logging.info(f"Отправлен сигнал: {signal}")

# Команды Telegram
@bot.message_handler(commands=['start'])
def handle_start(message):
    status['active'] = True
    bot.send_message(message.chat.id, "🟢 Сигналы включены")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    status['active'] = False
    bot.send_message(message.chat.id, "🔴 Сигналы отключены")

@bot.message_handler(commands=['status'])
def handle_status(message):
    state = "включены" if status['active'] else "отключены"
    bot.send_message(message.chat.id, f"⚙ Статус: сигналы {state}")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    bot.send_message(
        message.chat.id,
        f"📊 Статистика:\nCALL: {stats['CALL']}\nPUT: {stats['PUT']}\nВсего: {stats['total']}"
    )

# Основной цикл
def main_loop():
    logging.info("Бот запущен.")
    while True:
        if not status['active'] or not is_active_hours():
            time.sleep(5)
            continue

        candles = get_candles()
        if candles == 'limit_exceeded':
            logging.warning("Превышен лимит API. Ожидание 1 час.")
            time.sleep(3600)
            continue
        if not candles:
            logging.info("Данных нет или рынок закрыт.")
            time.sleep(60)
            continue

        signal = generate_signal(candles)
        if signal:
            logging.info("Задержка перед отправкой 20 секунд…")
            time.sleep(20)
            send_signal(signal)
        else:
            logging.info("Сигнал не сгенерирован.")
        time.sleep(40)  # 60 - 20 секунд задержки

# Запуск
if __name__ == '__main__':
    import threading
    threading.Thread(target=main_loop).start()
    bot.polling(none_stop=True)
