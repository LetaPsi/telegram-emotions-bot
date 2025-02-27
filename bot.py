import logging
import json
import os
import openpyxl
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Токен берется из переменной окружения
DATA_FILE = "diary.json"
EXCEL_FILE = "diary.xlsx"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def save_to_excel(data):
    if not os.path.exists(EXCEL_FILE):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Дата", "Пользователь", "Ситуация", "Факты", "Эмоции"])
    else:
        workbook = openpyxl.load_workbook(EXCEL_FILE)
        sheet = workbook.active

    for user_id, entries in data.items():
        for entry in entries:
            sheet.append([entry.get("дата", "Не указано"), user_id, entry["ситуация"], entry["факты"], entry["эмоции"]])

    workbook.save(EXCEL_FILE)

async def start(update: Update, context: CallbackContext):
    """Начало работы с ботом"""
    await update.message.reply_text("Привет! Я помогу вести твой дневник эмоций. Расскажи, что случилось?")

async def handle_text(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения от пользователя"""
    user_id = str(update.message.from_user.id)
    text = update.message.text

    data = load_data()
    if user_id not in data:
        data[user_id] = []

    # Сохраняем ситуацию в дневник
    data[user_id].append({
        "дата": update.message.date.strftime("%Y-%m-%d %H:%M:%S"),
        "ситуация": text,
        "факты": "",
        "эмоции": ""
    })

    save_data(data)
    save_to_excel(data)

    await update.message.reply_text("Я записал ситуацию. Теперь попробуй отделить факты от эмоций.")

async def export_data(update: Update, context: CallbackContext):
    """Отправка файла с дневником"""
    if os.path.exists(EXCEL_FILE):
        await update.message.reply_document(document=open(EXCEL_FILE, "rb"), filename="diary.xlsx", caption="Вот твой дневник 😊")
    else:
        await update.message.reply_text("Файл дневника пока пуст. Заполни его, отправляя записи!")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("export", export_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Запускаем Webhook вместо polling
    PORT = int(os.environ.get("PORT", 8443))  # Указываем порт
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/"
    )

if __name__ == "__main__":
    main()
