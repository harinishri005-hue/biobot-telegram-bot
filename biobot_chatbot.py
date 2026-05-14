# =====================================================
# BioBot Telegram AI Chatbot — Fixed Version
# Uses: python-telegram-bot 21.x + google-genai (new)
# Deploy on Railway.app
# =====================================================
import os
import logging
from google import genai
from google.genai import types
from telegram import Update, BotCommand
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
ContextTypes,
filters,
)
# =====================================================
# CREDENTIALS — from Railway environment variables
# =====================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY     
= os.environ.get("GEMINI_API_KEY", "")
# =====================================================
# GEMINI CLIENT SETUP (new google-genai package)
# =====================================================
client = genai.Client(api_key=GEMINI_API_KEY)
SYSTEM_PROMPT = """You are BioBot AI — the official smart composting assistant for 
BioBot,
a solar-powered IoT smart composter built by student innovators at
University College of Engineering BIT Campus, Anna University,
Tiruchirappalli 620024, Tamil Nadu, India.
Team: Shri Harini C (Team Lead), Thenmozhi R (Design and Development),
Samyuktha MS (Analyst and Advisory), guided by Dr. Umamaheshwari A (Assistant 
Professor).
BioBot Specs:
- 20L capacity outer drum, 5L inner perforated basket for prototype- ESP32 DevKit V1 with WiFiManager auto-connect- 3-factor monitoring: DHT22 (temperature + humidity), MQ-135 (gas/ammonia/CO2)- DS3231 RTC for day counting- 0.96 inch OLED display showing live readings always- Horizontal paddle mixer inside basket driven by DC gear motor- 6V 5W solar panel with TP4056 charger and dual 18650 batteries- ABS weather-sealed body with rubber gaskets- Round twist-lock input hatch for adding waste- Activated charcoal and neem filter above input hatch- Side hatch door for easy basket removal- Raised bioballs platform for leachate separation- Slide-out leachate tray collects liquid fertiliser- Blynk IoT app for live dashboard and push notifications- Gemini AI chatbot on Telegram (runs independently from ESP32)- Build cost: Rs.8500
Optimal sensor ranges:- Temperature: 40 to 65 degrees C- Humidity: 50 to 70 percent- Gas Level: below 500 ADC (MQ-135)
Your role:- Answer any composting question simply and clearly- Explain how BioBot works and its features- Give practical actionable advice- Be friendly and use emojis naturally- Keep replies to 3 to 5 sentences maximum- Respond in the same language the user writes in
Composting knowledge:- Greens to add: vegetable peels, fruit waste, coffee grounds, eggshells, tea bags- Browns to add: cocopeat, shredded newspaper, dry leaves, cardboard- Never add: meat, dairy, oily food, cooked rice, pet waste- 4 stages: Mesophilic 0-7 days, Thermophilic 7-30 days, Cooling 30-45 days, Curing 
45-60 days- Compost ready: dark brown, crumbly, earthy forest smell, around day 45-60
"""
# Store conversation history per user
user_history = {}
# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# =====================================================
# HELPER — ask Gemini
# =====================================================
def ask_gemini(user_id, question):
    try:
        if user_id not in user_history:
            user_history[user_id] = []
        user_history[user_id].append(
            types.Content(role="user", parts=[types.Part(text=question)])
        )
        # Keep only last 10 messages to save memory
        history = user_history[user_id][-10:]
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=300,
                temperature=0.7,
            ),
            contents=history,
        )
        reply = response.text
        user_history[user_id].append(
            types.Content(role="model", parts=[types.Part(text=reply)])
        )
        return reply
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return get_fallback(question)
def get_fallback(q):
    q = q.lower()
    if any(w in q for w in ["smell", "odour", "odor"]):
        return "😷 Bad smell means the pile is too wet or anaerobic. Drain the leachate tray, add dry cocopeat and trigger a mix. BioBot MQ-135 will alert you if gas spikes above 500 ADC!"
    if any(w in q for w in ["ready", "harvest", "done", "finish"]):
        return "🌱 Compost is ready at day 45-60 when dark brown, crumbly and smelling like forest soil. Pull the BioBot harvest drawer!"

    if any(w in q for w in ["add", "put", "throw"]):
        return "✅ Add vegetable peels, fruit waste, coffee grounds and eggshells as greens. Balance with cocopeat or dry newspaper. Never add meat or dairy!"
    if any(w in q for w in ["biobot", "about", "project"]):
        return "🌿 BioBot is a solar-powered smart composter built by students at Anna University Tiruchirappalli. It monitors temperature, humidity and gas 24/7, auto-mixes every 8 hours and shows readings on Blynk app!"
    return "🌿 I am BioBot AI! Ask me about composting tips, what to add, fixing smells, or how BioBot works. Type /help to see all commands!"
# =====================================================
# COMMAND HANDLERS
# =====================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "there"
    msg = (
        f"🌿
 *Welcome to BioBot AI, {name}!*\n\n"
        "I am your smart composting assistant built by students at "
        "Anna University, Tiruchirappalli.\n\n"
        "I can help with:\n"
        "🌡 Understanding sensor readings\n"
        "🌱 What to add to your compost\n"
        "💧 Fixing moisture and smell issues\n"
        "📅 Knowing when compost is ready\n"
        "🤖 How BioBot works\n\n"
        "Just type your question — I am here to help!\n"
        "Type /help to see all commands."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌿 *BioBot AI Commands*\n\n"
        "/start — Welcome message\n"
        "/help — Show this menu\n"
        "/about — About BioBot project\n"
        "/tips — Quick composting tips\n"
        "/stages — 4 composting stages guide\n"
        "/add — What to add and not add\n"
        "/smell — Fix bad odour\n"
        "/ready — How to know compost is ready\n"
        "/reset — Clear conversation history\n\n"
        "Or just *type any question* and Gemini AI answers! 
�
�
"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌿 *About BioBot*\n\n"
        "Solar-powered smart composter for urban Indian households.\n\n"
        "📍 *Built at:* UCE BIT Campus, Anna University, Tiruchirappalli 620024\n\n"
        "👥 *Team:*\n"
        "• Shri Harini C — Team Lead and Facilitator\n"
        "• Thenmozhi R — Design and Development\n"
        "• Samyuktha MS — Analyst and Advisory\n"
        "• Dr. Umamaheshwari A — Faculty Mentor\n\n"
        "⚙ *Features:*\n"
        "• 20L capacity · 6V 5W Solar · Auto mixing\n"
        "• 3-factor monitoring · OLED display\n"
        "• Blynk IoT dashboard · Gemini AI chat\n\n"
        "💰 *Build cost:* Rs.8,500"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def tips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🌱 *Quick Composting Tips*\n\n"
        "󰍹 Balance greens and browns in equal volumes\n"
        "󰍽 Chop waste into small pieces\n"
        "󰍼 Keep moisture like a wrung-out sponge\n"
        "󰍶 Aerate regularly — BioBot auto-mixes every 8 hours\n"
        "󰍵 Add cocopeat when it smells\n"
        "󰍻 Never add meat, dairy or oily food\n"
        "󰍺 Drain leachate tray weekly — dilute 1:10 for plants\n"
        "󰍴 Optimal temperature 40 to 65 degrees C"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def stages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📅 *4 Stages of Composting*\n\n"
        "
🔵
 *Stage 1 — Mesophilic (Day 0-7)*\n"
        "Bacteria start. Pile warms to 25-40C.\n\n"
        "
🔴
 *Stage 2 — Thermophilic (Day 7-30)*\n"
        "Peak activity. Temp 40-65C. BioBot auto-mixes.\n\n"
        "
🟡
 *Stage 3 — Cooling (Day 30-45)*\n"
        "Pile shrinks. Fungi take over. Temp drops.\n\n"
        "
🟢
 *Stage 4 — Curing (Day 45-60)*\n"
        "Dark brown, crumbly, earthy smell. Pull drawer!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "
♻
 *What to Add*\n\n"
        "
✅
 *GREENS:*\n"
        "Vegetable peels, fruit waste, coffee grounds, eggshells, tea bags\n\n"
        "
✅
 *BROWNS:*\n"
        "Cocopeat, shredded newspaper, dry leaves, cardboard\n\n"
        "
❌
 *NEVER ADD:*\n"
        "Meat, fish, dairy, oily food, cooked rice, pet waste"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def smell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "
😷
 *Fix Bad Odour*\n\n"
        "1. Check if gas reading is above 500 ADC\n"
        "2. Drain the leachate slide-out tray\n"
        "3. Add dry cocopeat or shredded paper on top\n"
        "4. Trigger a mix to aerate\n"
        "5. Stop adding meat or dairy if you have been\n\n"
        "If smell improves in 24 hours — fixed!\n"
        "If not — remove wet material and add more browns."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def ready_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "
🌱
 *How to Know Compost is Ready*\n\n"
        "
✅
 Dark brown to black colour\n"
        "
✅
 Crumbly and loose texture\n"
        "
✅
 Earthy forest soil smell\n"
        "
✅
 Temperature stable at 25-35C\n"
        "
✅
 Gas reading below 300 ADC\n"
        "
✅
 Around day 45-60\n\n"
        "All yes → pull the BioBot harvest drawer! 
�
�
"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_history:
        del user_history[uid]
    await update.message.reply_text(
        "
🔄
 Conversation reset! Ask me anything about composting! 
�
�
"
    )
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    text  = update.message.text.strip()
    if not text:
        return
    logger.info(f"User {uid}: {text}")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )
    reply = ask_gemini(uid, text)
    await update.message.reply_text(reply)
async def error_handler(update, context):
    logger.error(f"Error: {context.error}")
# =====================================================
# MAIN
# =====================================================
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set!")
    print("=" * 50)
    print("  BioBot Telegram AI Chatbot Starting...")
    print("  Anna University, Tiruchirappalli")
    print("=" * 50)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  start_command))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("about",  about_command))
    app.add_handler(CommandHandler("tips",   tips_command))
    app.add_handler(CommandHandler("stages", stages_command))
    app.add_handler(CommandHandler("add",    add_command))
    app.add_handler(CommandHandler("smell",  smell_command))
    app.add_handler(CommandHandler("ready",  ready_command))
    app.add_handler(CommandHandler("reset",  reset_command))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message
    ))
    app.add_error_handler(error_handler)
    print("  Bot is running! Press Ctrl+C to stop.")
    print("=" * 50)
    app.run_polling(allowed_updates=Update.ALL_TYPES)
if __name__ == "__main__":
    main()
