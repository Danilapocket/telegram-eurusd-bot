import logging
import pytz
from datetime import datetime, time as dtime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "123456789"))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

moscow_tz = pytz.timezone("Europe/Moscow")
start_hour = 8
end_hour = 0  # midnight

signals_enabled = True
stats = {"CALL": 0, "PUT": 0}

def is_within_working_hours():
    now = datetime.now(moscow_tz).time()
    return dtime(start_hour, 0) <= now or now < dtime(end_hour, 0)

def format_time():
    return datetime.now(moscow_tz).strftime("%H:%M:%S (UTC+3)")

def format_signal(direction: str):
    emoji = "🟢" if direction == "CALL" else "🔴"
    return f"{emoji} Сигнал по EUR/USD: {direction}\n🕒 Время: {format_time()}\n📉 Экспирация: 1 минута"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен. Сигналы будут приходить в рабочее время.")

async def enable_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global signals_enabled
    signals_enabled = True
    await update.message.reply_text("🟢 Сигналы включены")

async def disable_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global signals_enabled
    signals_enabled = False
    await update.message.reply_text("🔴 Сигналы выключены")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "включены" if signals_enabled else "выключены"
    await update.message.reply_text(f"⚙️ Статус: сигналы {status}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📊 Статистика:\nCALL: {stats['CALL']}\nPUT: {stats['PUT']}\nВсего: {stats['CALL'] + stats['PUT']}"
    )

async def send_signal(direction: str):
    if signals_enabled and is_within_working_hours():
        stats[direction] += 1
        message = format_signal(direction)
        await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("enable", enable_signals))
app.add_handler(CommandHandler("disable", disable_signals))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("stats", stats_command))

# Внутри своего кода вставляй вызов:
# await send_signal("CALL")  или  await send_signal("PUT")

if __name__ == "__main__":
    app.run_polling()
