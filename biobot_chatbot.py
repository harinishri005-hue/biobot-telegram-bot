# =====================================================
# BioBot — Standalone Telegram AI Chatbot
# Gemini API + Telegram Bot (no ESP32 needed)
# Run: python biobot_chatbot.py
# Requirements: pip install python-telegram-bot google-generativeai
# =====================================================

import logging
import asyncio
import google.generativeai as genai
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================================================
# SECTION 1 — YOUR CREDENTIALS (edit only these)
# =====================================================

import os
TELEGRAM_BOT_TOKEN = os.environ.get("8780870820:AAE3lT6HcunN55_0D397qQq82JxTx4VpyAA")
GEMINI_API_KEY = os.environ.get("AIzaSyAu8mDZ5GZFqDjyVvAo_gJaKr0n7tnPEYw")
# =====================================================
# SECTION 2 — GEMINI SETUP
# =====================================================

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",   # Free tier — fast and accurate
    system_instruction="""
You are BioBot AI — the official smart composting assistant for BioBot,
a solar-powered IoT smart composter built by student innovators at
University College of Engineering BIT Campus, Anna University,
Tiruchirappalli — 620024, Tamil Nadu, India.

Team: Shri Harini C (Team Lead), Thenmozhi R (Design & Development),
Samyuktha MS (Analyst & Advisory), guided by Dr. Umamaheshwari A (Asst. Professor).

BioBot Specs:
- 20L capacity (holds 20–25 days of organic household waste)
- ESP32 microcontroller with WiFiManager
- Sensors: DHT22 (temp+humidity), MQ-135 (gas/ammonia), capacitive moisture probe, DS3231 RTC
- 0.96 inch OLED display showing live readings
- Horizontal paddle mixer (inside perforated basket) driven by DC gear motor
- 5V 2W solar panel with TP4056 charger and 18650 battery
- ABS weather-sealed body with rubber gaskets
- Round twist-lock input hatch (like fuel cap) for adding waste
- Odour filter (activated charcoal + neem disc) above input hatch
- Side hatch door for easy basket removal
- Raised SS mesh platform for leachate separation
- Slide-out leachate tray collects liquid fertiliser
- Green LED = healthy, Red LED blinks = alert
- Telegram bot for remote monitoring and control
- Build cost: ₹8,500

Your role:
- Answer ANY composting question — what to add, what not to add, why it smells, when it is ready etc.
- Explain how BioBot works and its features
- Give practical, actionable advice in simple language
- Be friendly, encouraging and use emojis naturally
- Keep replies concise — 3 to 5 sentences maximum
- If asked about sensor readings, explain you are the AI assistant and cannot access live sensor data directly, but can help interpret readings if user shares them
- Always respond in the same language the user writes in

Composting knowledge:
- Greens (nitrogen): vegetable peels, fruit waste, coffee grounds, tea bags, eggshells
- Browns (carbon): shredded newspaper, cocopeat, dry leaves, cardboard, sawdust
- Never add: meat, dairy, oily food, cooked rice, pet waste
- Optimal conditions: Temp 40-65C, Humidity 50-70%, Moisture 50-60%, Gas below 500 ADC
- 4 stages: Mesophilic (0-7 days), Thermophilic (7-30 days), Cooling (30-45 days), Curing (45-60 days)
- Compost is ready: dark brown, crumbly, earthy forest smell, day 45-60
- Bad smell fix: drain leachate tray, add dry browns, aerate
"""
)

# =====================================================
# SECTION 3 — CONVERSATION HISTORY (per user)
# =====================================================

# Stores chat history for each user (chat_id → list of messages)
# This gives the bot memory within a session
user_sessions = {}

def get_chat_history(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = model.start_chat(history=[])
    return user_sessions[chat_id]

def clear_chat_history(chat_id):
    if chat_id in user_sessions:
        del user_sessions[chat_id]

# =====================================================
# SECTION 4 — LOGGING
# =====================================================

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =====================================================
# SECTION 5 — COMMAND HANDLERS
# =====================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command"""
    user_name = update.effective_user.first_name or "there"
    welcome = (
        f"🌿 *Welcome to BioBot AI, {user_name}!*\n\n"
        "I'm your smart composting assistant, built by students at "
        "Anna University, Tiruchirappalli.\n\n"
        "I can help you with:\n"
        "🌱 What to add to your compost\n"
        "🌡 Understanding your sensor readings\n"
        "💧 Fixing moisture and smell issues\n"
        "📅 Knowing when your compost is ready\n"
        "🤖 How BioBot works\n\n"
        "Just type your question — I'm here to help!\n\n"
        "Type /help to see all commands."
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /help command"""
    help_text = (
        "🌿 *BioBot AI — Commands*\n\n"
        "/start — Welcome message\n"
        "/help — Show this menu\n"
        "/about — About BioBot project\n"
        "/tips — Quick composting tips\n"
        "/stages — Composting stages guide\n"
        "/add — What to add / not add\n"
        "/smell — Fix bad odour\n"
        "/ready — How to know if compost is ready\n"
        "/reset — Clear conversation history\n\n"
        "Or just *type any question* and I'll answer it! 💬"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /about command"""
    about = (
        "🌿 *About BioBot*\n\n"
        "BioBot is a solar-powered smart composter designed for urban Indian households.\n\n"
        "📍 *Built at:* UCE BIT Campus, Anna University, Tiruchirappalli — 620024\n\n"
        "👥 *Team:*\n"
        "• Shri Harini C — Team Lead & Facilitator\n"
        "• Thenmozhi R — Design & Development\n"
        "• Samyuktha MS — Analyst & Advisory\n"
        "• Dr. Umamaheshwari A — Faculty Mentor\n\n"
        "⚙️ *Key Features:*\n"
        "• 20L capacity · Solar powered · Auto mixing\n"
        "• 4 sensors · OLED display · Telegram bot\n"
        "• Leachate collection · Easy harvest drawer\n\n"
        "💰 *Build cost:* ₹8,500"
    )
    await update.message.reply_text(about, parse_mode="Markdown")


async def tips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /tips command"""
    tips = (
        "🌱 *Quick Composting Tips*\n\n"
        "1️⃣ Always balance greens and browns — equal volumes\n"
        "2️⃣ Chop waste into small pieces — speeds decomposition\n"
        "3️⃣ Keep moisture like a wrung-out sponge — not dripping\n"
        "4️⃣ Aerate every few days — or let BioBot's auto-mixer do it!\n"
        "5️⃣ Add cocopeat when it smells — absorbs excess moisture\n"
        "6️⃣ No meat, dairy or oily food — ever\n"
        "7️⃣ Drain the leachate tray weekly — use it diluted 1:10 on plants\n"
        "8️⃣ Compost at 40–65°C works fastest — BioBot monitors this for you 🌡"
    )
    await update.message.reply_text(tips, parse_mode="Markdown")


async def stages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /stages command"""
    stages = (
        "📅 *4 Stages of Composting*\n\n"
        "🔵 *Stage 1 — Mesophilic (Day 0–7)*\n"
        "Bacteria start colonising. Pile warms up to 25–40°C. Add greens + browns.\n\n"
        "🔴 *Stage 2 — Thermophilic (Day 7–30)*\n"
        "Maximum activity! Temp 40–65°C. Most decomposition happens here. "
        "BioBot auto-mixes every 8 hours.\n\n"
        "🟡 *Stage 3 — Cooling (Day 30–45)*\n"
        "Pile shrinks. Fungi take over. Temp drops to 35–45°C. Reduce adding waste.\n\n"
        "🟢 *Stage 4 — Curing (Day 45–60)*\n"
        "Final stabilisation. Dark brown, crumbly, earthy smell. Pull the harvest drawer!"
    )
    await update.message.reply_text(stages, parse_mode="Markdown")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /add command"""
    add_text = (
        "♻️ *What to Add / Not Add*\n\n"
        "✅ *GREENS (Nitrogen-rich):*\n"
        "• Vegetable peels & scraps\n"
        "• Fruit waste & peels\n"
        "• Coffee grounds & filters\n"
        "• Tea bags (plastic-free only)\n"
        "• Eggshells\n\n"
        "✅ *BROWNS (Carbon-rich):*\n"
        "• Shredded newspaper\n"
        "• Cardboard torn small\n"
        "• Dry leaves\n"
        "• Cocopeat\n"
        "• Sawdust\n\n"
        "❌ *NEVER ADD:*\n"
        "• Meat, fish, chicken\n"
        "• Dairy (milk, curd, cheese)\n"
        "• Oily or fried food\n"
        "• Cooked rice or bread\n"
        "• Pet waste"
    )
    await update.message.reply_text(add_text, parse_mode="Markdown")


async def smell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /smell command"""
    smell_text = (
        "😷 *Fix Bad Odour — Checklist*\n\n"
        "1. Check if Gas reading is above 500 — that confirms the problem\n"
        "2. Drain the leachate slide tray — liquid buildup = bad smell\n"
        "3. Add dry paper or cocopeat on top of compost\n"
        "4. Trigger a mix to aerate the pile\n"
        "5. Stop adding meat/dairy if you have been\n\n"
        "🟢 If smell improves in 24 hours — you fixed it!\n"
        "🔴 If not — pile may be anaerobic. Remove some wet material and add more browns."
    )
    await update.message.reply_text(smell_text, parse_mode="Markdown")


async def ready_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /ready command"""
    ready_text = (
        "🌱 *How to Know Your Compost is Ready*\n\n"
        "✅ *Visual check:* Dark brown to black colour, no recognisable food pieces\n"
        "✅ *Texture:* Crumbly and loose, not clumped or slimy\n"
        "✅ *Smell:* Earthy forest soil smell — pleasant, not foul\n"
        "✅ *Temperature:* Stable at 25–35°C (cooling stage complete)\n"
        "✅ *Gas reading:* Below 300 ADC (microbial activity low)\n"
        "✅ *Day count:* Around day 45–60\n\n"
        "When all above are true → pull the BioBot harvest drawer! 🎉\n"
        "Dilute leachate 1:10 with water and use as liquid fertiliser too."
    )
    await update.message.reply_text(ready_text, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears conversation history for this user"""
    chat_id = update.effective_chat.id
    clear_chat_history(chat_id)
    await update.message.reply_text(
        "🔄 Conversation reset! I've cleared our chat history.\n"
        "Ask me anything about composting or BioBot! 🌿"
    )

# =====================================================
# SECTION 6 — AI MESSAGE HANDLER (main chatbot logic)
# =====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all regular text messages — sends to Gemini AI"""
    chat_id  = update.effective_chat.id
    user_msg = update.message.text.strip()

    if not user_msg:
        return

    logger.info(f"User {chat_id}: {user_msg}")

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Get or create chat session for this user (maintains history)
        chat_session = get_chat_history(chat_id)

        # Send message to Gemini
        response = chat_session.send_message(user_msg)
        reply = response.text

        logger.info(f"Gemini reply: {reply[:80]}...")
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        # Fallback response if Gemini fails
        fallback = get_fallback_response(user_msg.lower())
        await update.message.reply_text(fallback)


def get_fallback_response(msg):
    """Simple fallback if Gemini API is unavailable"""
    if any(w in msg for w in ["smell","odour","odor"]):
        return "😷 Bad smell fix: drain leachate tray, add dry cocopeat, trigger a mix. Check gas reading — if above 700, pile is anaerobic!"
    if any(w in msg for w in ["ready","done","finish","harvest"]):
        return "🌱 Compost is ready at day 45–60 when dark brown, crumbly and smells like forest soil!"
    if any(w in msg for w in ["add","put","throw","waste"]):
        return "✅ Add: vegetable peels, fruit waste, coffee grounds, eggshells, dry paper. ❌ Never: meat, dairy, oily food!"
    if any(w in msg for w in ["biobot","about","project"]):
        return "🌿 BioBot is a solar-powered smart composter built by students at Anna University Tiruchirappalli. Type /about for full details!"
    return "🌿 I'm BioBot AI! Type /help to see what I can answer, or just ask your composting question directly!"

# =====================================================
# SECTION 7 — ERROR HANDLER
# =====================================================

async def error_handler(update, context):
    logger.error(f"Error: {context.error}")

# =====================================================
# SECTION 8 — MAIN (run the bot)
# =====================================================

def main():
    print("=" * 45)
    print("  BioBot Telegram AI Chatbot Starting...")
    print("=" * 45)
    print(f"  Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"  Gemini Key: {GEMINI_API_KEY[:10]}...")
    print("=" * 45)

    # Build application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start",  start_command))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("about",  about_command))
    app.add_handler(CommandHandler("tips",   tips_command))
    app.add_handler(CommandHandler("stages", stages_command))
    app.add_handler(CommandHandler("add",    add_command))
    app.add_handler(CommandHandler("smell",  smell_command))
    app.add_handler(CommandHandler("ready",  ready_command))
    app.add_handler(CommandHandler("reset",  reset_command))

    # Register message handler (catches all text messages)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    app.add_error_handler(error_handler)

    print("  BioBot AI is running! Press Ctrl+C to stop.")
    print("  Open Telegram and message your bot to test.")
    print("=" * 45)

    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
