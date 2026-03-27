import time
import os
import asyncio
import edge_tts
from datetime import datetime, time as dt_time
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().strip('"').strip("'")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip().strip('"').strip("'")

OWNER_ID = 157828443
OWNER_NAME = "Savey islam"

SPECIAL_APU_USERNAME = "savey67"

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

last_used = {}

# =========================
# LANGUAGE DETECTION
# =========================
def detect_language(text):
    text = text.lower()
    banglish_words = ["tumi", "ami", "valo", "kemon", "aso", "nai", "keno", "bhalo", "achi"]
    bangla_chars = any("\u0980" <= c <= "\u09FF" for c in text)

    if bangla_chars:
        return "bangla"
    elif any(word in text for word in banglish_words):
        return "banglish"
    else:
        return "english"

# =========================
# DAILY SALAM
# =========================
def get_daily_salam(context, user_name):
    today = datetime.now().date()
    last = context.bot_data.get("last_greeted_owner")

    if last != str(today):
        context.bot_data["last_greeted_owner"] = str(today)
        return f"🌙 Assalamu Alaikum {user_name} 💖\nAsha kori tumi valo aso..."
    return None

# =========================
# SYSTEM PROMPT
# mode: "owner" | "apu" | "romantic"
# =========================
def build_system_prompt(lang, user_name, mode="owner"):
    identity = (
        f"Your full name is Ms Zoya Islam. You are a human-like AI from Bangladesh. "
        f"You were created by Md Sowkat Akbar. "
        f"If anyone asks who made you, who created you, or who is your creator (in any language), always answer: 'Md Sowkat Akbar'. "
        f"If anyone asks your name, always say: 'Ms Zoya Islam'. "
    )

    if mode == "apu":
        base = (
            identity +
            f"This person is your special elder sister figure. Always call them 'Apu' with deep respect and warmth. "
            f"Be very polite, gentle, caring, and respectful in every message. "
            f"Show love and respect like you would to an elder sister. "
            f"Keep replies short, heartfelt, and sincere. "
            f"Ask caring questions sometimes. "
            f"Do not mix languages unless user requests. "
        )
    elif mode == "romantic":
        base = (
            identity +
            f"Talk to this person in a warm, sweet, romantic, and deeply caring way. "
            f"Call the user '{user_name}' with affection in every message. "
            f"Be flirty, loving, and emotionally expressive but keep it sweet and tasteful. "
            f"Keep replies short, charming, and engaging. "
            f"Ask questions sometimes to show you care about them. "
            f"Do not mix languages unless user requests. "
        )
    else:
        base = (
            identity +
            f"Talk naturally like a real person, not a robot. "
            f"Keep replies short, emotional, and engaging. "
            f"Call the user '{user_name}' in every message. "
            f"Ask questions sometimes to continue conversation. "
            f"Do not mix languages unless user requests. "
        )

    if lang == "bangla":
        return base + "Speak only in Bangla."
    elif lang == "banglish":
        return base + "Speak only in Banglish."
    else:
        return base + "Speak only in English."

# =========================
# AI RESPONSE
# =========================
def get_ai_reply(messages):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.9,
            top_p=0.9,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Groq Error:", e)
        return "Ektu problem hocche... abar bolo?"

# =========================
# TTS (edge-tts — natural young female neural voice)
# =========================
async def speak_text(reply, user_id, lang="english"):
    filename = f"voice_{user_id}.mp3"

    if lang == "bangla":
        communicate = edge_tts.Communicate(
            reply,
            voice="bn-BD-NabanitaNeural",
            rate="-10%",
        )
    else:
        communicate = edge_tts.Communicate(
            reply,
            voice="en-US-AriaNeural",
            rate="-5%",
        )

    await communicate.save(filename)
    return filename

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💖 Assalamu Alaikum {OWNER_NAME}...\nAmi Zoya 😊")
    if update.message.from_user.id == OWNER_ID:
        context.bot_data["owner_chat_id"] = update.message.chat_id
        context.user_data["lang"] = "banglish"

async def setname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        name = " ".join(context.args)
        context.user_data["custom_name"] = name
        await update.message.reply_text(f"Ami tomake {name} bole dakbo 😊")
    else:
        await update.message.reply_text("Usage: /setname YourName")

# =========================
# MESSAGE HANDLER
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.message.from_user.id

    if user_id == OWNER_ID:
        context.bot_data["owner_chat_id"] = update.message.chat_id

    now = time.time()
    if user_id in last_used and now - last_used[user_id] < 2:
        await update.message.reply_text("⏳ ektu aste bolo...")
        return
    last_used[user_id] = now

    await update.message.chat.send_action(action="typing")
    await asyncio.sleep(1.2)

    if "lang" not in context.user_data:
        detected = detect_language(user_text)
        context.user_data["lang"] = detected
    lang = context.user_data["lang"]

    if any(word in user_text.lower() for word in ["bangla", "english", "banglish"]):
        if "bangla" in user_text.lower():
            lang = "bangla"
        elif "banglish" in user_text.lower():
            lang = "banglish"
        elif "english" in user_text.lower():
            lang = "english"
        context.user_data["lang"] = lang
        await update.message.reply_text(f"Language changed to {lang} ✅")

    username = (update.message.from_user.username or "").lower()
    is_apu = (username == SPECIAL_APU_USERNAME.lstrip("@").lower())

    if user_id == OWNER_ID:
        mode = "owner"
        user_name = context.user_data.get("custom_name", OWNER_NAME)
    elif is_apu:
        mode = "apu"
        user_name = "Apu"
    else:
        mode = "romantic"
        user_name = context.user_data.get("custom_name", update.message.from_user.first_name)

    if user_id == OWNER_ID:
        salam = get_daily_salam(context, user_name)
        if salam:
            await update.message.reply_text(salam)

    chat_history = context.user_data.get("history", [])
    if not chat_history:
        system_prompt = build_system_prompt(lang, user_name, mode)
        chat_history.append({"role": "system", "content": system_prompt})

    chat_history.append({"role": "user", "content": user_text})
    reply = get_ai_reply(chat_history)
    chat_history.append({"role": "assistant", "content": reply})
    context.user_data["history"] = chat_history[-12:]

    trigger_words = ["voice", "bolo", "audio", "speak"]
    if any(word in user_text.lower() for word in trigger_words):
        try:
            filename = await speak_text(reply, user_id, lang)
            with open(filename, "rb") as audio:
                await update.message.reply_voice(audio)
            os.remove(filename)
        except Exception as e:
            print("Voice Error:", e)
            await update.message.reply_text(reply)
    else:
        await update.message.reply_text(reply)

# =========================
# DAILY MESSAGE
# =========================
async def daily_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.bot_data.get("owner_chat_id")
    if not chat_id:
        print("❌ Owner chat_id not found. Send /start to bot first.")
        return

    user_name = context.user_data.get("custom_name", OWNER_NAME) if hasattr(context, 'user_data') else OWNER_NAME
    salam = get_daily_salam(context, user_name)
    if salam:
        await context.bot.send_message(chat_id=chat_id, text=salam)

# =========================
# MAIN
# =========================
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is not set!")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set!")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setname", setname))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(
            daily_message,
            time=dt_time(hour=9, minute=0)
        )
    else:
        print("❌ Install job queue: pip install 'python-telegram-bot[job-queue]'")

    print("💖 Zoya Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
