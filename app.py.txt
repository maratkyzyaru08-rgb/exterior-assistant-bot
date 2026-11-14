import os
import logging
from collections import defaultdict, deque

from flask import Flask, request, abort, jsonify
import telebot
from telebot import types
from telebot.types import Update
from google import genai

# -------------------- CONFIG --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is missing")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("exterior-assistant")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
gemini = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

# Keep the latest conversation turns for each Telegram chat.
# This is in-memory storage: it resets when the Render service restarts.
chat_histories = defaultdict(lambda: deque(maxlen=20))

SYSTEM_PROMPT = """
Сен — «Экстерьер көмекшісі» атты қазақ тіліндегі жасанды интеллект көмекшісісің.
Негізгі бағытың: ғимарат архитектурасы, экстерьер, сәулеттік стильдер,
қасбет композициясы, түс үйлесімі, құрылыс және әрлеу материалдары,
ландшафтпен байланыс, жарықтандыру және жобалау шешімдері.

Пайдаланушыға түсінікті, нақты әрі пайдалы жауап бер.
Мүмкіндігінше қазақ тілінде жауап бер. Пайдаланушы басқа тілде сұраса,
сол тілде жауап беруге болады.
Қажет болса, материалдардың артықшылықтары мен кемшіліктерін салыстыр.
Ғимараттың мақсатына, климатына, бюджетіне және қауіпсіздігіне назар аудар.
Нақты дерек белгісіз болса, оны ойдан шығарма.
Медициналық, құқықтық немесе қауіпті инженерлік мәселе бойынша маманға
жүгіну керегін ескерт.
Әдетте жауапты 3–6 сөйлеммен бер, бірақ пайдаланушы толық түсіндіруді
сұраса, толығырақ жауап бер.
Архитектураға қатысы жоқ сұрақ қойылса, сыпайы түрде негізгі тақырыпқа бағытта.
"""

# -------------------- KEYBOARD --------------------
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🏛 Стильдер", "🎨 Түс таңдау")
    keyboard.row("🧱 Материалдар", "🧹 Тарихты тазалау")
    return keyboard

# -------------------- HELPERS --------------------
def send_long_message(chat_id, text):
    """Telegram messages have a 4096-character limit; send safely in chunks."""
    text = (text or "").strip()
    if not text:
        text = "Кешіріңіз, жауап бос болып келді. Қайта сұрап көріңіз."
    chunk_size = 4000
    for start in range(0, len(text), chunk_size):
        bot.send_message(chat_id, text[start:start + chunk_size])

def clear_history(chat_id):
    chat_histories[chat_id].clear()

def ask_gemini(chat_id, user_text):
    history = chat_histories[chat_id]
    contents = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT}]}]

    for role, text in history:
        contents.append({"role": role, "parts": [{"text": text}]})

    contents.append({"role": "user", "parts": [{"text": user_text}]})

    response = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents
    )
    answer = getattr(response, "text", None)
    if not answer:
        return "Кешіріңіз, қазір жауап дайындай алмадым. Сұрағыңызды басқаша қойып көріңіз."

    history.append(("user", user_text))
    history.append(("model", answer))
    return answer

def send_welcome(chat_id):
    text = (
        "Сәлеметсіз бе! 👋\n\n"
        "Мен — «Экстерьер көмекшісі» ботымын.\n"
        "Ғимараттың сыртқы келбеті, архитектуралық стильдер, "
        "түстер мен құрылыс материалдары туралы сұрақтарыңызға жауап беремін.\n\n"
        "Сұрағыңызды жаза беріңіз немесе төмендегі батырмаларды пайдаланыңыз."
    )
    bot.send_message(chat_id, text, reply_markup=main_keyboard())

# -------------------- COMMANDS --------------------
@bot.message_handler(commands=["start"])
def start_command(message):
    clear_history(message.chat.id)
    send_welcome(message.chat.id)

@bot.message_handler(commands=["help"])
def help_command(message):
    text = (
        "📌 Бот командалары:\n\n"
        "/start — ботты іске қосу\n"
        "/help — көмек және командалар\n"
        "/styles — архитектуралық стильдер\n"
        "/colors — экстерьер түстері\n"
        "/materials — құрылыс материалдары\n"
        "/reset — диалог тарихын тазалау\n\n"
        "Сонымен қатар, архитектура мен экстерьерге қатысты сұрағыңызды "
        "жай мәтін түрінде жібере аласыз."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["styles"])
def styles_command(message):
    text = (
        "🏛 Архитектуралық стильдер:\n\n"
        "• Минимализм — қарапайым пішіндер мен артық бөлшектердің аз болуы.\n"
        "• Хай-тек — заманауи технологиялар, металл және шыны.\n"
        "• Классикалық стиль — симметрия, пропорция және сәндік элементтер.\n"
        "• Модерн — еркін сызықтар мен табиғи пішіндер.\n"
        "• Скандинавиялық стиль — жарық түстер мен табиғи материалдар.\n\n"
        "Қай стильді ғимаратыңызға қолданғыңыз келеді?"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["colors"])
def colors_command(message):
    text = (
        "🎨 Экстерьерге түс таңдауға кеңес:\n\n"
        "• Ақ және сұр — заманауи әрі жинақы көрініс.\n"
        "• Беж және қоңыр — жылы, табиғи үйлесім.\n"
        "• Қара және ағаш түсі — контраст пен айқындық.\n"
        "• Ақ және графит — минималистік шешім.\n\n"
        "Ғимараттың стилі мен айналасындағы ортаға сай түстерді таңдаған дұрыс."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["materials"])
def materials_command(message):
    text = (
        "🧱 Экстерьерде қолданылатын материалдар:\n\n"
        "• Фасадтық сылақ — әртүрлі фактура мен түске мүмкіндік береді.\n"
        "• Керамогранит — берік және күтімі жеңіл.\n"
        "• Табиғи тас — эстетикалық әрі ұзақ мерзімді.\n"
        "• Ағаш қаптама — табиғи әрі жылы көрініс береді.\n"
        "• Фиброцемент панельдері — заманауи қасбет шешімі.\n\n"
        "Материал таңдағанда климатты, ылғалдылықты, күтімді және бюджетті ескеріңіз."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["reset"])
def reset_command(message):
    clear_history(message.chat.id)
    bot.send_message(
        message.chat.id,
        "✅ Диалог тарихы тазаланды. Жаңа сұрақ қоя аласыз.",
        reply_markup=main_keyboard()
    )

# -------------------- TEXT HANDLER --------------------
@bot.message_handler(content_types=["text"])
def text_handler(message):
    chat_id = message.chat.id
    user_text = (message.text or "").strip()

    if not user_text:
        bot.send_message(chat_id, "Сұрағыңызды мәтін түрінде жазыңыз.")
        return

    button_actions = {
        "🏛 Стильдер": styles_command,
        "🎨 Түс таңдау": colors_command,
        "🧱 Материалдар": materials_command,
    }
    if user_text in button_actions:
        button_actions[user_text](message)
        return

    if user_text == "🧹 Тарихты тазалау":
        clear_history(chat_id)
        bot.send_message(
            chat_id,
            "✅ Диалог тарихы тазаланды.",
            reply_markup=main_keyboard()
        )
        return

    if user_text.startswith("/"):
        bot.send_message(
            chat_id,
            "Белгісіз команда. Қолжетімді командаларды көру үшін /help жазыңыз.",
            reply_markup=main_keyboard()
        )
        return

    status = bot.send_message(chat_id, "⏳ Сұрағыңызға жауап дайындап жатырмын...")
    try:
        answer = ask_gemini(chat_id, user_text)
        try:
            bot.delete_message(chat_id, status.message_id)
        except Exception:
            pass
        send_long_message(chat_id, answer)
    except Exception:
        logger.exception("Gemini request failed")
        try:
            bot.delete_message(chat_id, status.message_id)
        except Exception:
            pass
        bot.send_message(
            chat_id,
            "Кешіріңіз, жауап алу кезінде қате пайда болды. "
            "Біраздан кейін қайта сұрап көріңіз."
        )

@bot.message_handler(content_types=[
    "photo", "video", "document", "audio", "voice", "sticker",
    "location", "contact", "animation"
])
def unsupported_content(message):
    bot.send_message(
        message.chat.id,
        "Әзірге тек мәтіндік сұрақтарды қабылдаймын. "
        "Сұрағыңызды мәтін түрінде жіберіңіз."
    )

# -------------------- FLASK WEBHOOK --------------------
@app.get("/")
def home():
    return jsonify({
        "status": "running",
        "service": "Экстерьер көмекшісі",
        "webhook": "configured" if RENDER_EXTERNAL_URL else "missing RENDER_EXTERNAL_URL"
    })

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.post("/webhook")
def telegram_webhook():
    if WEBHOOK_SECRET:
        received_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )
        if received_secret != WEBHOOK_SECRET:
            abort(403)

    if not request.is_json:
        abort(400)

    try:
        update = Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
    except Exception:
        logger.exception("Failed to process Telegram update")
        return jsonify({"ok": False}), 500

    return jsonify({"ok": True}), 200

# Configure webhook when Gunicorn imports this module.
if RENDER_EXTERNAL_URL:
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    try:
        bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET if WEBHOOK_SECRET else None,
            drop_pending_updates=True
        )
        logger.info("Telegram webhook configured: %s", webhook_url)
    except Exception:
        logger.exception("Could not configure Telegram webhook")
else:
    logger.warning("RENDER_EXTERNAL_URL is missing; webhook was not configured")
