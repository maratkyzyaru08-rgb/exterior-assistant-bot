import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
from google import genai
from google.genai import types
from flask import Flask, request, abort

TOKEN = os.environ["BOT_TOKEN"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-3.5-flash-lite"

bot = telebot.TeleBot(TOKEN)
client = genai.Client(api_key=GEMINI_KEY)
app = Flask(__name__)
user_history = {}

SYSTEM_INSTRUCTION = """
Сен — Экстерьер көмекшісі атты архитектуралық ботсың.
Қасбет, экстерьер стильдері, түстер, құрылыс материалдары
және ғимарат дизайны бойынша кеңес бер.
Қазақ тілінде 3–6 сөйлеммен жауап бер.
Диалогтың алдыңғы хабарламаларын ескер.
Тақырыптан тыс сұрақтарға архитектураға бағытта.
Қауіпсіздік пен инженерлік есептерді маман тексеруі керек.
"""

keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(KeyboardButton("🏛 Экстерьер стильдері"),
             KeyboardButton("🎨 Қасбет түстері"))
keyboard.add(KeyboardButton("🧱 Құрылыс материалдары"))

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Сәлеметсіз бе! 🏠 Мен — Экстерьер көмекшісімін!\n"
        "Архитектура бойынша сұрағыңызды жазыңыз.",
        reply_markup=keyboard
    )

@bot.message_handler(commands=["help"])
def help_command(message):
    bot.reply_to(message,
        "/start — Бастау\n/help — Көмек\n"
        "/styles — Стильдер\n/colors — Түстер\n"
        "/materials — Материалдар\n/reset — Тарихты тазалау")

@bot.message_handler(commands=["reset"])
def reset(message):
    user_history.pop(message.chat.id, None)
    bot.reply_to(message, "🔄 Диалог тарихы тазаланды!")

@bot.message_handler(commands=["styles"])
@bot.message_handler(func=lambda m: m.text == "🏛 Экстерьер стильдері")
def styles(message):
    bot.reply_to(message,
        "🏛 Стильдер:\n1. Минимализм\n2. Классика\n"
        "3. Хай-тек\n4. Скандинавиялық стиль")

@bot.message_handler(commands=["colors"])
@bot.message_handler(func=lambda m: m.text == "🎨 Қасбет түстері")
def colors(message):
    bot.reply_to(message,
        "🎨 Түстер үйлесімі:\nАқ + сұр\nБеж + қоңыр\n"
        "Ақ + ағаш түсі\nҚара + ақ")

@bot.message_handler(commands=["materials"])
@bot.message_handler(func=lambda m: m.text == "🧱 Құрылыс материалдары")
def materials(message):
    bot.reply_to(message,
        "🧱 Материалдар:\nКірпіш\nСәндік сылақ\n"
        "Фиброцемент\nТабиғи тас")

@bot.message_handler(content_types=[
    "photo", "sticker", "video", "document",
    "voice", "audio", "animation", "location", "contact"
])
def non_text(message):
    bot.reply_to(message,
        "Мен әзірге тек мәтіндік хабарламаларды қабылдаймын.")

@bot.message_handler(content_types=["text"])
def ai_assistant(message):
    question = message.text.strip()
    chat_id = message.chat.id

    if question.startswith("/"):
        bot.reply_to(message, "Белгісіз команда. /help қараңыз.")
        return

    if len(question) > 4000:
        bot.reply_to(message, "Хабарлама тым ұзын. 4000 таңбаға дейін қысқартыңыз.")
        return

    try:
        history = user_history.get(chat_id, [])
        contents = history + [
            types.Content(role="user",
                parts=[types.Part.from_text(text=question)])
        ]

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )

        answer = response.text
        if not answer:
            bot.reply_to(message, "Жауап алынбады. Қайта сұрап көріңіз.")
            return

        if response.candidates and response.candidates[0].content:
            user_history[chat_id] = (
                contents + [response.candidates[0].content]
            )[-6:]

        for i in range(0, len(answer), 4000):
            bot.send_message(chat_id, answer[i:i+4000])

    except Exception as error:
        print("Gemini қатесі:", error)
        bot.reply_to(message,
            "⚠️ ЖИ қызметі уақытша қолжетімсіз. Кейінірек қайталап көріңіз.")

bot.set_my_commands([
    BotCommand("start", "Ботты іске қосу"),
    BotCommand("help", "Көмек"),
    BotCommand("styles", "Экстерьер стильдері"),
    BotCommand("colors", "Қасбет түстері"),
    BotCommand("materials", "Құрылыс материалдары"),
    BotCommand("reset", "Диалог тарихын тазалау")
])

@app.route("/", methods=["GET"])
def home():
    return "Exterior Assistant is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    secret = os.getenv("WEBHOOK_SECRET")
    if secret and request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != secret:
        abort(403)

    update = telebot.types.Update.de_json(
        request.get_data().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "OK", 200

url = os.getenv("RENDER_EXTERNAL_URL")
if url:
    bot.set_webhook(
        url=url + "/webhook",
        secret_token=os.getenv("WEBHOOK_SECRET")
    )
