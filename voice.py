import logging
import os
import openai
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import TELEGRAM_TOKEN, OPENAI_API_KEY, WEBHOOK_URL

# Настройка OpenAI API
openai.api_key = OPENAI_API_KEY

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем Flask-сервер
app = Flask(__name__)

# Инициализация Telegram бота
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Обработчик команды /start
async def start(update: Update, context):
    await update.message.reply_text("Привет! Я готов обрабатывать твои голосовые и текстовые сообщения.")

# Обработчик текстовых сообщений
async def handle_text(update: Update, context):
    await update.message.reply_text(f"Ты написал: {update.message.text}")

# Обработчик голосовых сообщений с Whisper
async def handle_voice(update: Update, context):
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        # Скачиваем голосовое сообщение
        file_path = f"voice_{update.message.chat_id}.ogg"
        await file.download_to_drive(file_path)

        # Расшифровка через Whisper
        with open(file_path, "rb") as audio_file:
            response = openai.Audio.transcribe("whisper-1", audio_file)

        transcribed_text = response.get("text", "").strip()
        os.remove(file_path)

        if transcribed_text:
            await update.message.reply_text(f"🔹 Расшифрованный текст:\n{transcribed_text}")
        else:
            await update.message.reply_text("⚠️ Не удалось расшифровать голос.")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка при обработке голосового сообщения.")

# Добавляем обработчики в приложение
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_handler(MessageHandler(filters.VOICE, handle_voice))

# Обработчик для Webhook
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Принимает запросы от Telegram"""
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

# Установка Webhook при запуске
async def set_webhook():
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")

if __name__ == "__main__":
    logger.info("🚀 Запуск Flask-сервера...")
    import asyncio
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=5000)

