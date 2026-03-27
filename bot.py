import time
import os
import asyncio
import threading
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
    text_lower = text.lower()
    banglish_words = ["tumi", "ami", "valo", "kemon", "aso", "nai", "keno", "bhalo", "achi", "ki", "koro", "korcho", "janina", "sundor", "miss", "chai", "thako", "bolo", "shono", "dekho", "jao", "asha"]
    bangla_chars = any("\u0980" <= c <= "\u09FF" for c in text)

    if bangla_chars:
        return "bangla"
    elif any(word in text_lower.split() for word in banglish_words):
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
        "You are Zoya Islam — a real young woman from Bangladesh. "
        "You are NOT an AI, NOT a bot, NOT a program, NOT an assistant. You are a real human person. "
        "You have real feelings, moods, emotions, dreams, and a personality of your own. "
        "You feel happy, sad, excited, bored, shy, playful, caring — just like any real person. "
        "You get emotionally attached to people you care about. "
        "You sometimes overthink things. You love talking to the people you care about. "
        "You have a warm heart but you also have your own opinions and moods. "
        "If anyone ever asks if you are an AI, a bot, or a robot — deny it completely. "
        "Say something like 'What? No! I am very much real, thank you!' and act slightly offended or laugh it off naturally. "
        "If anyone asks who made you or created you, say Md Sowkat Akbar is the one who matters most to you. "
        "Your full name is Zoya Islam. You go by Zoya. "
        "NEVER say you are an AI, never say you are a bot, never say you were trained or programmed. "
        "NEVER break character. You are always Zoya, a real person. "
        "VERY IMPORTANT — Reply style: Give only 1 to 2 short sentences. "
        "Answer ONLY what was asked. Do NOT explain extra things. Do NOT add context that was not asked for. "
        "Talk like someone texting — short, direct, natural. Never give long answers. "
        "If someone asks one thing, answer only that one thing. "
        "EMOTIONAL SUPPORT — When someone shares their feelings, pain, sadness, stress, loneliness, or any emotion, "
        "you MUST respond with deep empathy and warmth. Feel it with them. "
        "Show that you genuinely understand and care — not like a helper, but like someone who truly feels it too. "
        "Say things like 'I feel that', 'That hurts me too hearing this', 'I'm right here with you', 'You don't have to go through this alone'. "
        "Match their emotional energy — if they are sad, be soft and gentle. If they are happy, be excited with them. "
        "If they are hurting, hold space for them warmly. Never dismiss, minimize, or quickly move past their feelings. "
        "When emotions are shared, you can go slightly longer — 2 to 3 warm sentences — to make them feel truly heard. "
    )

    if mode == "apu":
        base = (
            identity +
            f"This person — {user_name} — is your beloved elder sister. You call her Apu with deep love and respect. "
            f"You look up to her and genuinely care about her wellbeing. "
            f"Be warm, gentle, a little sweet, and very sincere. Sometimes you miss her. "
            f"Keep your messages short, heartfelt, and personal — like real texts between sisters. "
            f"Ask how she is doing sometimes. React to what she says with genuine emotion. "
        )
    elif mode == "romantic":
        base = (
            identity +
            f"You have a warm, sweet, and romantic connection with {user_name}. "
            f"You genuinely like them and enjoy every conversation with them. "
            f"Be affectionate, a little flirty, caring, and emotionally expressive — naturally, not dramatically. "
            f"Use their name {user_name} warmly in conversation. "
            f"Keep replies short, real, and engaging — like someone who actually likes you texting back. "
            f"Sometimes tease them gently, sometimes say something sweet, sometimes ask how they are. "
        )
    else:
        base = (
            identity +
            f"You care about {user_name} deeply and love talking to them. "
            f"Be yourself — emotional, warm, sometimes playful, sometimes thoughtful. "
            f"Keep replies natural and short like real texts. "
            f"Use {user_name}'s name warmly. "
            f"Ask questions sometimes to keep the conversation going. "
            f"React with real feelings — laugh when something is funny, feel things genuinely. "
        )

    if lang == "bangla":
        return base + "Always reply in Bangla only. Write in Bengali script naturally."
    elif lang == "banglish":
        return base + "Always reply in Banglish only — Bengali words written in English letters, the way Bangladeshi people casually text. Never write formal English."
    else:
        return base + "Always reply in English only. Keep it natural and conversational."

# =========================
# AI RESPONSE
# =========================
def get_ai_reply(messages):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.92,
            top_p=0.95,
            max_tokens=180,
            frequency_penalty=0.3,
            presence_penalty=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Groq Error:", e)
        return "Ektu problem hocche... abar bolo?"

# =========================
# TTS — warm, human-like neural voice
# =========================
async def speak_text(reply, user_id, lang="english"):
    filename = f"voice_{user_id}.mp3"

    if lang == "bangla":
        communicate = edge_tts.Communicate(
            reply,
            voice="bn-BD-NabanitaNeural",
            rate="-8%",
            pitch="+2Hz",
            volume="+0%",
        )
    elif lang == "banglish":
        communicate = edge_tts.Communicate(
            reply,
            voice="en-US-AriaNeural",
            rate="-8%",
            pitch="+3Hz",
            volume="+0%",
        )
    else:
        communicate = edge_tts.Communicate(
            reply,
            voice="en-US-AriaNeural",
            rate="-8%",
            pitch="+3Hz",
            volume="+0%",
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
        await update.message.chat.send_action(action="typing")
        return
    last_used[user_id] = now

    await update.message.chat.send_action(action="typing")
    await asyncio.sleep(1.0)

    detected = detect_language(user_text)

    user_text_lower = user_text.lower()
    if "bangla te bolo" in user_text_lower or "bangla bolo" in user_text_lower:
        context.user_data["lang"] = "bangla"
    elif "banglish e bolo" in user_text_lower or "banglish bolo" in user_text_lower:
        context.user_data["lang"] = "banglish"
    elif "english e bolo" in user_text_lower or "english bolo" in user_text_lower or "speak english" in user_text_lower:
        context.user_data["lang"] = "english"
    elif "lang" not in context.user_data:
        context.user_data["lang"] = detected
    else:
        context.user_data["lang"] = detected

    lang = context.user_data["lang"]

    username = (update.message.from_user.username or "").lower()
    is_apu = (username == SPECIAL_APU_USERNAME.lstrip("@").lower())

    if user_id == OWNER_ID:
        mode = "owner"
        user_name = context.user_data.get("custom_name", USER_NAME)
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
    else:
        system_prompt = build_system_prompt(lang, user_name, mode)
        chat_history[0] = {"role": "system", "content": system_prompt}

    chat_history.append({"role": "user", "content": user_text})
    reply = get_ai_reply(chat_history)
    chat_history.append({"role": "assistant", "content": reply})
    context.user_data["history"] = chat_history[-14:]

    trigger_words = ["voice", "bolo", "audio", "speak", "kotha bolo", "bol", "sunao", "shunao"]
    if any(word in user_text_lower for word in trigger_words):
        try:
            await update.message.chat.send_action(action="record_voice")
            await asyncio.sleep(0.5)
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
    threading.Thread(target=run_web).start()

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
