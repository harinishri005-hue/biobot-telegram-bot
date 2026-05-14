#  =====================================================
# BioBot Telegram AI Chatbot — FULLY FIXED VERSION
# Uses: python-telegram-bot==20.7 + google-genai
# Deploy on Railway / Koyeb / HuggingFace
# =====================================================
# requirements.txt must contain exactly:
#   python-telegram-bot==20.7
#   google-genai
# =====================================================
 
import os
import logging
import asyncio
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
 
# =====================================================
# LOGGING SETUP
# =====================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
 
# =====================================================
# CREDENTIALS — ALWAYS from environment variables
# NEVER paste real keys here in code
# Add in Railway → Variables tab:
#   TELEGRAM_BOT_TOKEN = your token
#   GEMINI_API_KEY     = your key
# =====================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY")
 
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set! Add it in Railway Variables tab.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set! Add it in Railway Variables tab.")
 
# =====================================================
# GEMINI CLIENT — initialized once cleanly
# Model: gemini-1.5-flash (correct name, highest free quota)
# Do NOT call any model here at top level — only inside functions
# =====================================================
client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash-lite"  # Correct model name — do not change
 
# =====================================================
# SYSTEM PROMPT
# =====================================================
SYSTEM_PROMPT = """You are BioBot AI — the official smart composting assistant for
BioBot, a solar-powered IoT smart composter built by student innovators at
University College of Engineering BIT Campus, Anna University,
Tiruchirappalli 620024, Tamil Nadu, India.
 
Team: Shri Harini C (Team Lead), Thenmozhi R (Design and Development),
Samyuktha MS (Analyst and Advisory), guided by Dr. Umamaheshwari A (Assistant Professor).
 
BioBot Specs:
- 20L capacity outer drum, inner perforated basket
- ESP32 DevKit V1 with WiFiManager auto-connect
- 3-factor monitoring: DHT22 (temperature + humidity), MQ-135 (gas/ammonia/CO2)
- DS3231 RTC for day counting
- 0.96 inch OLED display showing live readings
- Paddle mixer inside basket driven by DC gear motor (5s forward + 5s backward)
- 6V 5W solar panel with TP4056 charger and 18650 battery
- HDPE body with round twist-lock input hatch
- Activated charcoal and neem filter above input hatch
- Side hatch door for basket removal
- Slide-out leachate tray
- Blynk IoT app for live dashboard and push notifications
- Gemini AI chatbot on Telegram (runs independently from ESP32)
- Build cost: Rs 8500
- Made in Tamil Nadu, India
 
Optimal sensor ranges:
- Temperature: 40 to 65 degrees C (thermophilic phase)
- Humidity: 50 to 70 percent
- Gas Level: below 500 ADC is safe, above 700 is danger
 
Your role:
- Answer composting questions simply and clearly
- Explain how BioBot works and its features
- Give practical actionable advice
- Be friendly, warm and encouraging
- Use emojis naturally
- Keep replies to 3 to 5 sentences for simple questions
- Use bullet points for step-by-step advice
- Respond in the same language the user writes in
 
Composting knowledge:
- Greens to add: vegetable peels, fruit waste, coffee grounds, eggshells, tea bags
- Browns to add: cocopeat, shredded newspaper, dry leaves, cardboard
- Never add: meat, dairy, oily food, cooked rice, pet waste, plastic, metal
- 4 stages: Mesophilic 0-7 days, Thermophilic 7-30 days, Cooling 30-45 days, Curing 45-60 days
- Compost ready: dark brown, crumbly, earthy forest smell, around day 45-60"""
 
# =====================================================
# CONVERSATION HISTORY — per user memory
# =====================================================
user_history = {}
 
# =====================================================
# GEMINI AI FUNCTION — async with retry logic
# =====================================================
async def ask_gemini(user_id: int, question: str) -> str:
    """
    Calls Gemini API with full conversation history.
    Retries automatically on quota errors.
    Notifies user clearly if quota is exceeded.
    """
    # Initialise history for new users
    if user_id not in user_history:
        user_history[user_id] = []
 
    # Add user message to history
    user_history[user_id].append(
        types.Content(
            role="user",
            parts=[types.Part(text=question)]
        )
    )
 
    # Keep only last 10 messages to save memory and tokens
    history = user_history[user_id][-10:]
 
    # Retry up to 3 times with 45 second wait on quota errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=350,
                    temperature=0.7,
                ),
                contents=history,
            )
            reply = response.text
 
            # Save model reply to history
            user_history[user_id].append(
                types.Content(
                    role="model",
                    parts=[types.Part(text=reply)]
                )
            )
            return reply
 
        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini attempt {attempt + 1} error: {error_str[:200]}")
 
            # Handle quota exceeded error
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    wait_seconds = 45
                    logger.warning(
                        f"Quota limit hit. Waiting {wait_seconds}s before retry {attempt + 2}..."
                    )
                    await asyncio.sleep(wait_seconds)
                    continue
                else:
                    # All retries exhausted — tell user clearly
                    logger.error("All retries exhausted. Quota exceeded.")
                    return (
                        "⚠️ *AI Quota Temporarily Exhausted*\n\n"
                        "BioBot AI has reached its hourly request limit.\n\n"
                        "🕐 *What to do:*\n"
                        "• Wait 1 hour and try again — quota resets automatically\n"
                        "• Use /tips, /add, /smell or /stages for instant offline answers\n"
                        "• Daily quota resets at midnight\n\n"
                        "This is a free tier limitation and is normal. "
                        "Your bot is working correctly! 🌱"
                    )
 
            # Handle model not found error
            elif "404" in error_str or "NOT_FOUND" in error_str:
                logger.error("Model not found error — check GEMINI_MODEL name.")
                return (
                    "⚠️ AI model configuration error.\n"
                    "Please contact the BioBot team.\n\n"
                    + get_fallback(question)
                )
 
            # Handle invalid API key
            elif "401" in error_str or "UNAUTHENTICATED" in error_str:
                logger.error("Invalid Gemini API key!")
                return (
                    "⚠️ AI authentication error.\n"
                    "API key may be invalid or expired.\n\n"
                    + get_fallback(question)
                )
 
            # All other errors — use fallback
            else:
                logger.error(f"Unknown Gemini error: {error_str[:300]}")
                return get_fallback(question)
 
    return get_fallback(question)
 
 
def get_fallback(q: str) -> str:
    """Offline answers for common questions when AI is unavailable."""
    q = q.lower()
    if any(w in q for w in ["smell", "odour", "odor", "stink"]):
        return (
            "😷 Bad smell means anaerobic conditions.\n\n"
            "Fix steps:\n"
            "• Drain the leachate slide-out tray\n"
            "• Add dry cocopeat or shredded paper on top\n"
            "• Trigger a mix to aerate\n"
            "• Stop adding meat or dairy\n"
            "• Open lid briefly to ventilate\n\n"
            "Healthy compost smells earthy like forest soil! 🌱"
        )
    if any(w in q for w in ["ready", "harvest", "done", "finish"]):
        return (
            "🌱 Compost is ready at day 45 to 60 when:\n\n"
            "• Dark brown or black colour\n"
            "• Crumbly and loose texture\n"
            "• Earthy forest soil smell\n"
            "• Temperature stable near room temperature\n"
            "• Gas below 300 ADC\n\n"
            "All yes → pull the BioBot harvest drawer! 🎉"
        )
    if any(w in q for w in ["add", "put", "throw", "what can"]):
        return (
            "♻️ What to add to BioBot:\n\n"
            "✅ Greens: vegetable peels, fruit waste, coffee grounds, eggshells, tea bags\n"
            "✅ Browns: cocopeat, shredded newspaper, dry leaves, cardboard\n\n"
            "❌ Never add: meat, fish, dairy, oily food, cooked rice, pet waste, plastic"
        )
    if any(w in q for w in ["biobot", "about", "project", "spec"]):
        return (
            "🌿 BioBot is a 20L solar-powered smart composter built by students at "
            "Anna University, Tiruchirappalli.\n\n"
            "It monitors temperature, humidity and gas 24/7, auto-mixes every 8 hours, "
            "shows readings on Blynk app and costs Rs 8500 to build!"
        )
    if any(w in q for w in ["temperature", "temp", "hot", "cold"]):
        return (
            "🌡️ Ideal compost temperature is 40 to 65 degrees C.\n\n"
            "• Below 35C: add nitrogen waste (fruit peels, coffee) and mix\n"
            "• Above 70C: sprinkle water and mix immediately\n"
            "• 28 to 42C: compost is curing — nearly ready!"
        )
    if any(w in q for w in ["humidity", "wet", "dry", "moisture"]):
        return (
            "💧 Ideal humidity is 50 to 70 percent.\n\n"
            "• Too dry: sprinkle water lightly, add wet scraps\n"
            "• Too wet: add dry cocopeat or paper, drain leachate tray\n"
            "• Squeeze test: handful should clump but not drip"
        )
    return (
        "🌿 I am BioBot AI! Ask me about:\n"
        "• What to add to compost\n"
        "• Fixing bad smells\n"
        "• Temperature and humidity\n"
        "• When compost is ready\n"
        "• How BioBot works\n\n"
        "Type /help to see all commands!"
    )
 
# =====================================================
# TELEGRAM COMMAND HANDLERS
# =====================================================
 
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "there"
    await update.message.reply_text(
        f"🌿 *Welcome to BioBot AI, {name}!*\n\n"
        "I am your smart composting assistant built by students at "
        "Anna University, Tiruchirappalli.\n\n"
        "I can help with:\n"
        "🌡️ Understanding sensor readings\n"
        "🌱 What to add to your compost\n"
        "💧 Fixing moisture and smell issues\n"
        "📅 Knowing when compost is ready\n"
        "🤖 How BioBot works\n\n"
        "Just type your question — Gemini AI will answer!\n"
        "Type /help to see all commands.",
        parse_mode="Markdown"
    )
 
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌿 *BioBot AI Commands*\n\n"
        "/start   — Welcome message\n"
        "/help    — Show this menu\n"
        "/about   — About BioBot project\n"
        "/tips    — Quick composting tips\n"
        "/stages  — 4 composting stages guide\n"
        "/add     — What to add and not add\n"
        "/smell   — Fix bad odour\n"
        "/ready   — How to know compost is ready\n"
        "/reset   — Clear conversation history\n\n"
        "💬 Or just *type any question* and Gemini AI answers!",
        parse_mode="Markdown"
    )
 
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌿 *About BioBot*\n\n"
        "Solar-powered smart composter for urban Indian households.\n\n"
        "📍 *Built at:* UCE BIT Campus, Anna University, Tiruchirappalli 620024\n\n"
        "👥 *Team:*\n"
        "• Shri Harini C — Team Lead and Facilitator\n"
        "• Thenmozhi R — Design and Development\n"
        "• Samyuktha MS — Analyst and Advisory\n"
        "• Dr. Umamaheshwari A — Faculty Mentor\n\n"
        "⚙️ *Features:*\n"
        "• 20L capacity · 6V 5W Solar · Auto mixing\n"
        "• DHT22 + MQ-135 monitoring · OLED display\n"
        "• Blynk IoT dashboard · Gemini AI chat\n\n"
        "💰 *Build cost:* Rs 8,500\n"
        "🏫 *Made in Tamil Nadu, India* 🌱",
        parse_mode="Markdown"
    )
 
async def tips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌱 *Quick Composting Tips*\n\n"
        "• Balance greens and browns in equal volumes\n"
        "• Chop waste into smaller pieces for faster breakdown\n"
        "• Keep moisture like a wrung-out sponge\n"
        "• BioBot auto-mixes every 8 hours — keeps it aerated\n"
        "• Add cocopeat immediately when it smells bad\n"
        "• Never add meat, dairy or oily food\n"
        "• Drain leachate tray weekly — dilute 1:10 for plants\n"
        "• Optimal temperature 40 to 65 degrees C\n"
        "• Eggshells add calcium — great addition!\n"
        "• Coffee grounds are nitrogen-rich — add freely ☕",
        parse_mode="Markdown"
    )
 
async def stages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 *4 Stages of Composting*\n\n"
        "🔵 *Stage 1 — Mesophilic (Day 0 to 7)*\n"
        "Bacteria start breaking down waste.\n"
        "Temperature rises slowly to 25 to 40C.\n\n"
        "🔴 *Stage 2 — Thermophilic (Day 7 to 30)*\n"
        "Peak activity! Temperature 40 to 65C.\n"
        "BioBot auto-mixes to keep oxygen flowing.\n\n"
        "🟡 *Stage 3 — Cooling (Day 30 to 45)*\n"
        "Pile shrinks. Fungi take over. Temp drops.\n\n"
        "🟢 *Stage 4 — Curing (Day 45 to 60)*\n"
        "Dark brown, crumbly, earthy smell.\n"
        "Pull the BioBot harvest drawer! 🎉",
        parse_mode="Markdown"
    )
 
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "♻️ *What to Add to BioBot*\n\n"
        "✅ *GREENS (Nitrogen-rich):*\n"
        "Vegetable peels, fruit waste, coffee grounds,\n"
        "eggshells, tea bags, fresh grass clippings\n\n"
        "✅ *BROWNS (Carbon-rich):*\n"
        "Cocopeat, shredded newspaper, dry leaves,\n"
        "cardboard, paper bags\n\n"
        "❌ *NEVER ADD:*\n"
        "Meat, fish, dairy, oily food, cooked rice,\n"
        "pet waste, plastic, metal, glass\n\n"
        "📌 Ratio: 1 part greens : 1 part browns",
        parse_mode="Markdown"
    )
 
async def smell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "😷 *Fix Bad Odour*\n\n"
        "Bad smell = anaerobic — not enough oxygen.\n\n"
        "*Fix steps:*\n"
        "1. Drain the leachate slide-out tray\n"
        "2. Add dry cocopeat or paper on top\n"
        "3. Trigger a mix to aerate\n"
        "4. Check — meat or dairy in bin? Remove it.\n"
        "5. Open lid 10 minutes to ventilate\n\n"
        "*Smell types:*\n"
        "• Earthy = healthy ✅\n"
        "• Ammonia = too much nitrogen — add browns\n"
        "• Rotten egg = too wet — mix and drain\n"
        "• Sweet = too much fruit — add dry material",
        parse_mode="Markdown"
    )
 
async def ready_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌱 *How to Know Compost is Ready*\n\n"
        "✅ Dark brown to black colour\n"
        "✅ Crumbly and loose texture\n"
        "✅ Earthy forest soil smell — not rotten\n"
        "✅ Temperature stable at 25 to 35C\n"
        "✅ Gas reading below 300 ADC\n"
        "✅ Around day 45 to 60\n\n"
        "All yes → pull the BioBot harvest drawer!\n"
        "Blynk app also notifies you when ready 🎉",
        parse_mode="Markdown"
    )
 
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_history:
        del user_history[uid]
    await update.message.reply_text(
        "🔄 Conversation history cleared!\n"
        "Fresh start — ask me anything! 🌱"
    )
 
# =====================================================
# MAIN MESSAGE HANDLER
# All text messages → Gemini AI
# =====================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    text = update.message.text.strip()
    name = update.effective_user.first_name or "User"
 
    if not text:
        return
 
    logger.info(f"Message from {name} (ID:{uid}): {text[:100]}")
 
    # Show typing indicator while AI thinks
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
 
    # Get AI response (async with retry)
    reply = await ask_gemini(uid, text)
 
    await update.message.reply_text(reply, parse_mode="Markdown")
 
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Telegram error: {context.error}")
 
# =====================================================
# MAIN ENTRY POINT
# Uses Application.run_polling — NOT Updater (removed in v20)
# =====================================================
def main():
    print("=" * 50)
    print("  BioBot Telegram AI Chatbot")
    print("  Anna University, Tiruchirappalli")
    print(f"  Model: {GEMINI_MODEL}")
    print(f"  Token: {'SET' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
    print(f"  Gemini: {'SET' if GEMINI_API_KEY else 'MISSING'}")
    print("=" * 50)
 
    # Build app using Application builder (v20+ correct method)
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )
 
    # Register all command handlers
    app.add_handler(CommandHandler("start",   start_command))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("about",   about_command))
    app.add_handler(CommandHandler("tips",    tips_command))
    app.add_handler(CommandHandler("stages",  stages_command))
    app.add_handler(CommandHandler("add",     add_command))
    app.add_handler(CommandHandler("smell",   smell_command))
    app.add_handler(CommandHandler("ready",   ready_command))
    app.add_handler(CommandHandler("reset",   reset_command))
 
    # All other text → Gemini AI
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
 
    # Error handler
    app.add_error_handler(error_handler)
 
    print("  Bot is running! Waiting for messages...")
    print("=" * 50)
 
    # Start polling — drop any messages received while bot was offline
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
 
if __name__ == "__main__":
    main()
