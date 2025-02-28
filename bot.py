import os
import logging
import json
import openai
import openpyxl
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Загружаем переменные окружения из .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настраиваем OpenAI
openai.api_key = OPENAI_API_KEY

# Файл для сохранения данных
EXCEL_FILE = "diary.xlsx"

# Включаем логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Функция для отправки запроса в ChatGPT
def analyze_text(text):
    prompt = f"""
    Проанализируй следующий текст: {text}
    Определи:
    1. Искажения, которые транслирует мне мой патологический критик.
    2. Мои эмоции.
    3. Факты.
    4. Наводящие вопросы, чтобы помочь мне разобраться в этой ситуации.
    5. Варианты, как я могу обезоружить критика.

    Ответ должен быть в формате JSON:
    {{
        "distortion": "Описание искажений и анализа критика",
        "comment": "Как можно обезоружить критика"
    }}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "Ты - опытный психолог."}, {"role": "user", "content": prompt}],
        temperature=0.7
    )

    try:
        result = json.loads(response["choices"][0]["message"]["content"])
        return result
    except (KeyError, json.JSONDecodeError):
        return {"distortion": "Ошибка анализа.", "comment": "Попробуй позже."}

# Функция сохранения данных в Excel
def save_to_excel(situation, distortion, comment):
    if not os.path.exists(EXCEL_FILE):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Ситуация", "Искажение", "Опровержение"])
    else:
        workbook = openpyxl.load_workbook(EXCEL_FILE)
        sheet = workbook.active

    sheet.append([situation, distortion, comment])
    workbook.save(EXCEL_FILE)

# Команда /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Расскажи, что у тебя случилось (можно голосом или текстом).")

# Обработчик аудио (транскрипция + анализ)
async def handle_voice(update: Update, context: CallbackContext):
    user = update.message.from_user
    voice = update.message.voice

    # Запрашиваем транскрипцию у Telegram
    transcript = voice.transcribe()

    if not transcript:
        await update.message.reply_text("Не удалось распознать голос. Попробуй еще раз.")
        return

    # Анализируем текст с ChatGPT
    result = analyze_text(transcript)

    # Сохраняем в дневник
    save_to_excel(transcript, result["distortion"], result["comment"])

    # Отправляем пользователю результат
    await update.message.reply_text(f"Разбор:\n\nИскажения:\n{result['distortion']}\n\nОпровержение:\n{result['comment']}")

# Обработчик текстовых сообщений
async def handle_text(update: Update, context: CallbackContext):
    user_text = update.message.text

    # Анализируем текст с ChatGPT
    result = analyze_text(user_text)

    # Сохраняем в дневник
    save_to_excel(user_text, result["distortion"], result["comment"])

    # Отправляем пользователю результат
    await update.message.reply_text(f"Разбор:\n\nИскажения:\n{result['distortion']}\n\nОпровержение:\n{result['comment']}")

# Команда /export (отправка дневника)
async def export_data(update: Update, context: CallbackContext):
    if os.path.exists(EXCEL_FILE):
        await update.message.reply_document(document=open(EXCEL_FILE, "rb"), filename="diary.xlsx", caption="Вот твой дневник 📖")
    else:
        await update.message.reply_text("Файл дневника пока пуст.")

# Основная функция бота
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики команд и сообщений
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("export", export_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()