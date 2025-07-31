import time
import requests
import telebot
import logging
from datetime import datetime, timedelta
import threading

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
            if data.get('code') == 429:
                return 'limit_exceeded'
            return None
        return data.get('values')
    except Exception as e:
        logging.error(f"Ошибка при запросе котировок: {e}")
        return None

# Генерация сигнала
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
    return None

# Проверка по времени UTC+3
def is_working_hours():
    now = datetime.utcnow() + timedelta(hours=3)
    return 8 <= now.hour < 24

# Отправка сигнала
def send_signal(signal):
    global last_signal
    if signal == last_signal:
        logging.info("Повтор сигнала, не отправляем.")
        return
    last_signal = signal
    stats[signal] += 1
    stats['total'] += 1

    now = datetime.utcnow() + timedelta(hours=3)
    formatted_time = now.strftime('%H:%M:%S')

    emoji = "🟢" if signal == 'CALL' else "🔴"
    color = "<b><u><span style='color:green'>CALL</span></u></b>" if signal == 'CALL' else "<b><u><span style='color:red'>PUT</span></u></b>"

    text = f"{emoji} Сигнал по EUR/USD: {signal}\n🕐 Время: {formatted_time} UTC+3"
    bot.send_message(TELEGRAM_CHAT_ID, text, parse_mode="HTML")
    logging.info(f"Сигнал отправлен: {signal}")

# Основной цикл
def signal_loop():
    logging.info("Цикл сигналов запущен.")
    while True:
        if not status['active']:
            time.sleep(5)
            continue
        if not is_working_hours():
            logging.info("Вне рабочего времени.")
            time.sleep(60)
            continue
        candles = get_candles()
        if candles == 'limit_exceeded':
            logging.warning("API лимит. Ждём 1 час.")
            time.sleep(3600)
            continue
        if not candles:
            logging.info("Нет данных.")
            time.sleep(60)
            continue
        signal = generate_signal(candles)
        if signal:
            send_signal(signal)
        else:
            logging.info("Сигнал не сгенерирован.")
        time.sleep(45)  # Сигнал за 15 сек до новой свечи

# Команды
@bot.message_handler(commands=['start'])
def cmd_start(message):
    status['active'] = True
    bot.send_message(message.chat.id, "🟢 Сигналы включены")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    status['active'] = False
    bot.send_message(message.chat.id, "🔴 Сигналы отключены")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    state = "включены" if status['active'] else "отключены"
    bot.send_message(message.chat.id, f"⚙ Статус: сигналы {state}")

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    bot.send_message(
        message.chat.id,
        f"📊 Статистика:\nCALL: {stats['CALL']}\nPUT: {stats['PUT']}\nВсего: {stats['total']}"
    )

# Запуск
if __name__ == '__main__':
    threading.Thread(target=signal_loop).start()
    bot.polling(none_stop=True)
