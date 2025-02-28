import os
import logging
import openai
import pandas as pd
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

# Загрузка переменных из .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask сервер для вебхука
app = Flask(__name__)

# Файл для хранения дневника эмоций
EXCEL_FILE = "emotions_journal.xlsx"

# Функция для анализа текста через OpenAI
def analyze_text(text):
    prompt = f"""
    Проанализируй ситуацию: "{text}".
    1. Определи, какие искажения транслирует патологический критик.
    2. Какие эмоции присутствуют в этой ситуации?
    3. Выдели факты из ситуации.
    4. Сформулируй наводящие вопросы для анализа.
    5. Как можно обезоружить патологического критика?
    Ответ оформи в формате:
    - Искажения: ...
    - Эмоции: ...
    - Факты: ...
    - Вопросы: ...
    - Как обезоружить критика: ...
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response["choices"][0]["message"]["content"].strip()

# Функция для сохранения данных в Excel
def save_to_excel(text, analysis):
    data = {
        "Ситуация": [text],
        "Искажения": [analysis.get("Искажения", "")],
        "Эмоции": [analysis.get("Эмоции", "")],
        "Факты": [analysis.get("Факты", "")],
        "Опровержение": [analysis.get("Как обезоружить критика", "")]
    }
    df = pd.DataFrame(data)

    try:
        existing_df = pd.read_excel(EXCEL_FILE)
        df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        pass

    df.to_excel(EXCEL_FILE, index=False)

# Функция обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Расскажи, что у тебя случилось?")

# Функция обработки текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text("Анализирую ситуацию...")
    
    # Отправляем запрос в OpenAI
    analysis = analyze_text(user_message)

    # Разбираем текст ответа
    analysis_dict = {}
    for line in analysis.split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            analysis_dict[key.strip()] = value.strip()

    # Сохраняем в Excel
    save_to_excel(user_message, analysis_dict)

    # Отправляем пользователю разбор
    await update.message.reply_text(f"Разбор ситуации:\n{analysis}")

# Функция установки вебхука
async def set_webhook(application):
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Вебхук установлен: {webhook_url}")
# Функция обработки входящих обновлений
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
async def webhook():
    request_data = request.get_json()
    update = Update.de_json(request_data, bot)
    await application.process_update(update)
    return "OK", 200

# Основная функция
def main():
    global application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Запускаем Flask сервер
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
