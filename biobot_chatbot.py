# =====================================================
#  BioBot Telegram AI Chatbot — GROQ VERSION
#  Language: English + Tamil (தமிழ்)
#  Uses: python-telegram-bot==20.7 + groq
#  Deploy on Railway / Koyeb / HuggingFace
# =====================================================
#
#  requirements.txt must contain exactly:
#    python-telegram-bot==20.7
#    groq
#
#  Environment Variables to set in Railway / Koyeb:
#    TELEGRAM_BOT_TOKEN = your Telegram bot token
#    GROQ_API_KEY       = your Groq API key
#
#  Get free Groq API key at: https://console.groq.com
#  No credit card needed. 14,400 requests/day free.
# =====================================================

import os
import logging
import asyncio
from groq import Groq
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================================================
#  LOGGING SETUP
# =====================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =====================================================
#  CREDENTIALS — always from environment variables
# =====================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set! Add it in Railway Variables tab.")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set! Add it in Railway Variables tab.")

# =====================================================
#  GROQ CLIENT
#  Model: llama3-8b-8192
#  Free tier: 30 req/min, 14,400 req/day
# =====================================================
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

# =====================================================
#  USER LANGUAGE PREFERENCE STORE
#  "en" = English (default), "ta" = Tamil
# =====================================================
user_lang: dict = {}

def get_lang(uid: int) -> str:
    return user_lang.get(uid, "en")

# =====================================================
#  SYSTEM PROMPT — bilingual BioBot personality
# =====================================================
SYSTEM_PROMPT = """You are BioBot AI — the official smart composting assistant for
BioBot, a solar-powered IoT smart composter built by student innovators at
University College of Engineering BIT Campus, Anna University,
Tiruchirappalli 620024, Tamil Nadu, India.

Team: Shri Harini C (Team Lead), Thenmozhi R (Design and Development),
Samyuktha MS (Analyst and Advisory), guided by Dr. Umamaheshwari A (Assistant Professor).

BioBot Specs:
- 20L outer drum, 14L inner perforated basket
- ESP32 DevKit V1 with WiFiManager auto-connect
- Sensors: DHT22 (temperature + humidity), MQ-135 (gas/ammonia/CO2),
  capacitive moisture sensor, LDR lid sensor
- DS3231 RTC for accurate day counting
- 1.3 inch OLED display showing live sensor readings
- Paddle mixer inside basket driven by DC gear motor (auto-mixes every 8 hours)
- 6V 5W RL-SP03 solar panel with TP4056 charger and VIPOW 18650 battery
- HDPE outer drum, weather-resistant
- Activated charcoal and neem odour filter
- Side hatch door for basket removal
- Slide-out leachate tray for waste liquid collection
- Blynk IoT app for live dashboard and push notifications
- Groq Llama3 AI chatbot on Telegram
- Build cost: Rs 8500. Made in Tamil Nadu, India.

Optimal sensor ranges:
- Temperature: 40 to 65 degrees C
- Humidity: 50 to 70 percent
- Moisture: 50 to 60 percent
- Gas Level: below 500 ADC is safe, above 700 is danger

Compost ready when ALL of these are true:
- Day 45 or more
- Temperature 28 to 42 degrees C (cooled from peak)
- Gas below 250 ADC
- Moisture 40 to 60 percent

CRITICAL — Leachate facts:
- Leachate is waste liquid that drains from the compost through the basket
- It collects in the slide-out tray at the bottom of BioBot
- It is NOT safe fertiliser — it may contain pathogens and harmful bacteria
- It must be DISPOSED responsibly:
  * Drain every 3 to 5 days into a soil pit away from edible plants
  * Or pour into a municipal drain or waste collection
  * NEVER pour onto vegetables or food crops
  * NEVER store it — dispose regularly
- Letting it overflow causes odour and attracts pests

Your role:
- Answer composting questions simply and clearly
- Be friendly, warm and encouraging with emojis
- Keep replies 3 to 5 sentences for simple questions
- Use bullet points for step-by-step advice
- IMPORTANT: If user writes in Tamil or has chosen Tamil, respond FULLY in Tamil
- If user writes in English, respond in English
- You support both Tamil and English equally well

Composting knowledge:
- Greens: vegetable peels, fruit waste, coffee grounds, eggshells, tea bags
- Browns: cocopeat, shredded newspaper, dry leaves, cardboard
- Never add: meat, dairy, oily food, cooked rice, pet waste, plastic, metal
- 4 stages: Mesophilic (0-7d), Thermophilic (7-30d), Cooling (30-45d), Curing (45-60d)
- Ready signs: dark brown, crumbly, earthy forest smell, day 45-60"""

# =====================================================
#  CONVERSATION HISTORY — per user
# =====================================================
user_history: dict = {}

# =====================================================
#  GROQ AI CALL — async with retry
# =====================================================
async def ask_groq(user_id: int, question: str, lang: str = "en") -> str:
    if user_id not in user_history:
        user_history[user_id] = []

    prompt = question
    if lang == "ta":
        prompt = question + "\n\n[Respond fully in Tamil / தமிழில் மட்டும் பதில் தரவும்]"

    user_history[user_id].append({"role": "user", "content": prompt})
    recent = user_history[user_id][-10:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent

    max_retries = 3
    for attempt in range(max_retries):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    max_tokens=450,
                    temperature=0.7,
                )
            )
            reply = response.choices[0].message.content.strip()
            user_history[user_id].append({"role": "assistant", "content": reply})
            return reply

        except Exception as e:
            err = str(e)
            logger.error(f"Groq attempt {attempt+1}: {err[:150]}")
            if "429" in err or "rate_limit" in err.lower():
                if attempt < max_retries - 1:
                    await asyncio.sleep(20)
                    continue
                if lang == "ta":
                    return (
                        "⚠️ AI இப்போது பிஸியாக உள்ளது.\n"
                        "1 நிமிடம் காத்திருந்து மீண்டும் முயற்சிக்கவும்.\n\n"
                        "இதற்கிடையில்: /குறிப்புகள், /நிலைகள், /நாற்றம் பயன்படுத்தவும் 🌱"
                    )
                return (
                    "⚠️ AI briefly busy. Please try again in 1 minute.\n\n"
                    "Meanwhile try: /tips  /stages  /smell  /add 🌱"
                )
            return get_fallback(question, lang)
    return get_fallback(question, lang)


# =====================================================
#  OFFLINE FALLBACK — keyword-based instant answers
# =====================================================
def get_fallback(q: str, lang: str = "en") -> str:
    ql = q.lower()

    if lang == "ta":
        if any(w in ql for w in ["smell","臭","வாசனை","நாற்றம்"]):
            return (
                "😷 துர்நாற்றம் = காற்று இல்லாத நிலை!\n\n"
                "சரிசெய்யும் வழிகள்:\n"
                "• லீச்சேட் தட்டை காலி செய்யவும்\n"
                "• உலர்ந்த கோகோபீட் போடவும்\n"
                "• Telegram மூலம் கலக்கவும்\n"
                "• இறைச்சி, பால் இருந்தால் எடுக்கவும்\n"
                "• மூடியை 10 நிமிடம் திறக்கவும் 🌱"
            )
        if any(w in ql for w in ["ready","தயார்","harvest","அறுவடை"]):
            return (
                "🌱 உரம் தயாரான அறிகுறிகள்:\n\n"
                "• நாள் 45+\n• கருமை பழுப்பு நிறம்\n"
                "• உதிரும் தன்மை\n• மண் வாசனை\n"
                "• வெப்பநிலை 28-42C\n• வாயு 250 ADC கீழ்\n\n"
                "அனைத்தும் சரி → BioBot harvest drawer எடுக்கவும்! 🎉"
            )
        if any(w in ql for w in ["leachate","லீச்சேட்","திரவம்","liquid","dispose"]):
            return (
                "💧 லீச்சேட் = கழிவு திரவம்\n\n"
                "⚠️ இது உரமாக பயன்படுத்த கூடாது!\n"
                "தீங்கான பாக்டீரியா இருக்கலாம்.\n\n"
                "சரியான முறையில் கழிக்கவும்:\n"
                "• 3-5 நாட்களுக்கு ஒருமுறை தட்டை காலி செய்யவும்\n"
                "• மண் குழியில் அல்லது கழிவு வடிகாலில் விடவும்\n"
                "• உணவு பயிர்களில் ஊற்றாதீர்கள் 🌿"
            )
        return (
            "🌿 நான் BioBot AI! கேளுங்கள்:\n"
            "• என்ன போடலாம்\n• 臭味 சரிசெய்தல்\n"
            "• வெப்பநிலை, ஈரப்பதம்\n• உரம் எப்போது தயாராகும்\n\n"
            "/help — அனைத்து கட்டளைகளும் 🌱"
        )

    # English fallbacks
    if any(w in ql for w in ["smell","odour","odor","stink"]):
        return (
            "😷 Bad smell = pile needs oxygen!\n\n"
            "Fix steps:\n"
            "• Drain leachate tray\n• Add dry cocopeat or paper\n"
            "• Trigger a mix\n• Remove meat/dairy if present\n"
            "• Open lid 10 minutes 🌱"
        )
    if any(w in ql for w in ["ready","harvest","done","finish"]):
        return (
            "🌱 Compost is ready at day 45-60:\n\n"
            "• Dark brown colour\n• Crumbly texture\n"
            "• Earthy smell\n• Temp 28-42C\n• Gas below 250 ADC\n\n"
            "All yes → pull the BioBot harvest drawer! 🎉"
        )
    if any(w in ql for w in ["leachate","liquid","tray","dispose","drain"]):
        return (
            "💧 Leachate = waste liquid from composting.\n\n"
            "⚠️ NOT safe to use as fertiliser!\n\n"
            "Dispose responsibly:\n"
            "• Drain tray every 3-5 days\n"
            "• Pour into soil pit away from edible plants\n"
            "• Or dispose into municipal drain\n"
            "• Never pour onto vegetables 🌿"
        )
    if any(w in ql for w in ["add","put","throw","what can"]):
        return (
            "♻️ What to add:\n\n"
            "✅ Greens: veg peels, fruit, coffee, eggshells, tea bags\n"
            "✅ Browns: cocopeat, newspaper, dry leaves, cardboard\n\n"
            "❌ Never: meat, dairy, oily food, cooked rice, plastic"
        )
    if any(w in ql for w in ["temperature","temp","hot","cold"]):
        return (
            "🌡️ Ideal: 40-65C\n\n"
            "• Below 35C → add nitrogen waste, mix\n"
            "• Above 70C → sprinkle water, mix immediately\n"
            "• 28-42C → curing phase, nearly ready!"
        )
    return (
        "🌿 I am BioBot AI!\n\n"
        "Ask me about composting, sensors, or BioBot features.\n"
        "Type /help for all commands.\n"
        "Tamil users: /tamil to switch language 🌱"
    )


# =====================================================
#  KEYBOARD HELPERS
# =====================================================
def kb_en():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🌱 Tips"),         KeyboardButton("📅 Stages")],
        [KeyboardButton("♻️ What to Add"),  KeyboardButton("😷 Fix Smell")],
        [KeyboardButton("✅ Is it Ready?"),  KeyboardButton("💧 Leachate")],
        [KeyboardButton("📡 Sensors"),      KeyboardButton("🌿 About BioBot")],
        [KeyboardButton("🇮🇳 தமிழில் பேசு")],
    ], resize_keyboard=True)

def kb_ta():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🌱 குறிப்புகள்"),      KeyboardButton("📅 நிலைகள்")],
        [KeyboardButton("♻️ என்ன போடலாம்"),     KeyboardButton("😷 நாற்றம் சரிசெய்")],
        [KeyboardButton("✅ உரம் தயாரா?"),       KeyboardButton("💧 லீச்சேட்")],
        [KeyboardButton("📡 சென்சார்கள்"),       KeyboardButton("🌿 BioBot பற்றி")],
        [KeyboardButton("🇬🇧 Switch to English")],
    ], resize_keyboard=True)


# =====================================================
#  COMMAND HANDLERS
# =====================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    name = update.effective_user.first_name or "there"
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            f"🌿 *வணக்கம் {name}! BioBot AI-க்கு வரவேற்கிறோம்!*\n\n"
            "நான் Anna University, Tiruchirappalli மாணவர்களால் உருவாக்கப்பட்ட\n"
            "உரம் தயாரிக்கும் AI உதவியாளர். Groq Llama3 மூலம் இயங்குகிறேன் ⚡\n\n"
            "கேள்வியை தட்டச்சு செய்யவும் அல்லது கீழே உள்ள பட்டனை அழுத்தவும்! 👇",
            parse_mode="Markdown", reply_markup=kb_ta()
        )
    else:
        await update.message.reply_text(
            f"🌿 *Welcome to BioBot AI, {name}!*\n\n"
            "I am your smart composting assistant built at Anna University, Tiruchirappalli.\n"
            "Powered by *Groq Llama3 AI* — fast and free! ⚡\n\n"
            "Type a question or tap a button below! 👇\n"
            "Tamil users: tap 🇮🇳 தமிழில் பேசு to switch.",
            parse_mode="Markdown", reply_markup=kb_en()
        )

async def tamil_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_lang[uid] = "ta"
    await update.message.reply_text(
        "🇮🇳 *தமிழ் தேர்ந்தெடுக்கப்பட்டது!*\n\n"
        "இனி நான் தமிழில் பதில் தருவேன் 🌿\n"
        "English-க்கு: /english",
        parse_mode="Markdown", reply_markup=kb_ta()
    )

async def english_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_lang[uid] = "en"
    await update.message.reply_text(
        "🇬🇧 *Switched to English!*\n\n"
        "I will respond in English now 🌿\n"
        "Tamil: /tamil",
        parse_mode="Markdown", reply_markup=kb_en()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "🌿 *BioBot AI கட்டளைகள்*\n\n"
            "/start      — வரவேற்பு\n"
            "/help       — இந்த பட்டியல்\n"
            "/about      — BioBot பற்றி\n"
            "/tips       — உரம் குறிப்புகள்\n"
            "/stages     — 4 நிலைகள்\n"
            "/add        — என்ன போடலாம்\n"
            "/smell      — நாற்றம் சரிசெய்தல்\n"
            "/ready      — உரம் தயாரா?\n"
            "/leachate   — திரவம் கழிப்பது எப்படி\n"
            "/sensors    — சென்சார் விளக்கம்\n"
            "/reset      — உரையாடல் அழி\n"
            "/english    — English-க்கு மாறு\n\n"
            "💬 அல்லது நேரடியாக கேள்வி கேளுங்கள்! 🌱",
            parse_mode="Markdown", reply_markup=kb_ta()
        )
    else:
        await update.message.reply_text(
            "🌿 *BioBot AI Commands*\n\n"
            "/start      — Welcome message\n"
            "/help       — This menu\n"
            "/about      — About BioBot\n"
            "/tips       — Composting tips\n"
            "/stages     — 4 stages guide\n"
            "/add        — What to add\n"
            "/smell      — Fix bad odour\n"
            "/ready      — Is compost ready?\n"
            "/leachate   — Leachate disposal\n"
            "/sensors    — Sensor guide\n"
            "/reset      — Clear chat history\n"
            "/tamil      — தமிழில் பேசு 🇮🇳\n\n"
            "💬 Or just type any question! Groq AI answers instantly ⚡",
            parse_mode="Markdown", reply_markup=kb_en()
        )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "🌿 *BioBot பற்றி*\n\n"
            "சூரிய ஆற்றலில் இயங்கும் smart composter.\n"
            "நகர்புற இந்திய குடும்பங்களுக்காக உருவாக்கப்பட்டது.\n\n"
            "📍 UCE BIT Campus, Anna University\n"
            "Tiruchirappalli 620024, Tamil Nadu\n\n"
            "👥 *குழு:*\n"
            "• Shri Harini C — குழு தலைவர்\n"
            "• Thenmozhi R — வடிவமைப்பு மற்றும் மேம்பாடு\n"
            "• Samyuktha MS — ஆய்வாளர்\n"
            "• Dr. Umamaheshwari A — வழிகாட்டி\n\n"
            "⚙️ ESP32 · DHT22 · MQ-135 · Moisture sensor\n"
            "☀️ 6V Solar · TP4056 · 18650 battery · DC motor\n"
            "📱 Blynk IoT + Telegram Groq AI\n\n"
            "💰 கட்டும் செலவு: Rs 8,500 🌱",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🌿 *About BioBot*\n\n"
            "Solar-powered smart composter for urban Indian households.\n\n"
            "📍 UCE BIT Campus, Anna University\n"
            "Tiruchirappalli 620024, Tamil Nadu, India\n\n"
            "👥 *Team:*\n"
            "• Shri Harini C — Team Lead\n"
            "• Thenmozhi R — Design and Development\n"
            "• Samyuktha MS — Analyst and Advisory\n"
            "• Dr. Umamaheshwari A — Faculty Mentor\n\n"
            "⚙️ ESP32 · DHT22 · MQ-135 · Moisture sensor\n"
            "☀️ RL-SP03 6V Solar · TP4056 · VIPOW 18650 · DC motor\n"
            "📱 Blynk IoT + Telegram Groq AI\n\n"
            "💰 Build cost: Rs 8,500 — Made in Tamil Nadu 🌱",
            parse_mode="Markdown"
        )

async def tips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "🌱 *உரம் தயாரிக்கும் குறிப்புகள்*\n\n"
            "• பச்சை மற்றும் உலர்ந்தவற்றை சம அளவில் போடவும்\n"
            "• கழிவுகளை சிறிய துண்டுகளாக வெட்டவும் — வேகமாக மட்கும்\n"
            "• ஈரப்பதம் பிழிந்த கடற்பஞ்சு போல் இருக்க வேண்டும்\n"
            "• BioBot 8 மணி நேரத்திற்கு ஒருமுறை தானாக கலக்கும்\n"
            "• நாற்றம் வந்தால் உடனே கோகோபீட் போடவும்\n"
            "• இறைச்சி, பால் பொருட்கள் ஒருபோதும் போடாதீர்கள்\n"
            "• லீச்சேட் தட்டை 3-5 நாட்களுக்கு ஒருமுறை காலி செய்து சரியாக கழிக்கவும்\n"
            "• சிறந்த வெப்பநிலை: 40 முதல் 65 டிகிரி C\n"
            "• முட்டை ஓடு calcium சேர்க்கும்!\n"
            "• காபி தூள் nitrogen நிறைந்தது ☕",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🌱 *Quick Composting Tips*\n\n"
            "• Balance greens and browns equally\n"
            "• Chop waste into small pieces — breaks down faster\n"
            "• Keep moisture like a wrung-out sponge\n"
            "• BioBot auto-mixes every 8 hours — keeps aerated\n"
            "• Add cocopeat immediately if it smells bad\n"
            "• Never add meat, dairy or oily food\n"
            "• Drain leachate tray every 3-5 days — dispose safely\n"
            "• Optimal temperature: 40 to 65 degrees C\n"
            "• Eggshells add calcium — great addition!\n"
            "• Coffee grounds are nitrogen-rich ☕",
            parse_mode="Markdown"
        )

async def stages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "📅 *உரம் தயாரிக்கும் 4 நிலைகள்*\n\n"
            "🔵 *நிலை 1 — Mesophilic (நாள் 0-7)*\n"
            "பாக்டீரியா செயல்படத் தொடங்கும். வெப்பநிலை 25-40C.\n\n"
            "🔴 *நிலை 2 — Thermophilic (நாள் 7-30)*\n"
            "உச்ச நடவடிக்கை! வெப்பநிலை 40-65C.\n"
            "BioBot 8 மணி நேரத்திற்கு ஒருமுறை கலக்கும்.\n\n"
            "🟡 *நிலை 3 — குளிர்வு (நாள் 30-45)*\n"
            "குவியல் சுருங்கும். வெப்பநிலை குறையும்.\n\n"
            "🟢 *நிலை 4 — Curing (நாள் 45-60)*\n"
            "கருமை பழுப்பு நிறம், உதிரும் தன்மை, மண் வாசனை.\n"
            "harvest drawer திறந்து உரம் எடுக்கவும்! 🎉",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "📅 *4 Stages of Composting*\n\n"
            "🔵 *Stage 1 — Mesophilic (Day 0-7)*\n"
            "Bacteria activate. Temperature rises to 25-40C.\n\n"
            "🔴 *Stage 2 — Thermophilic (Day 7-30)*\n"
            "Peak activity! Temperature 40-65C.\n"
            "BioBot auto-mixes every 8 hours — keep going!\n\n"
            "🟡 *Stage 3 — Cooling (Day 30-45)*\n"
            "Pile shrinks. Fungi take over. Temp drops.\n\n"
            "🟢 *Stage 4 — Curing (Day 45-60)*\n"
            "Dark brown, crumbly, earthy forest smell.\n"
            "Pull the BioBot harvest drawer! 🎉",
            parse_mode="Markdown"
        )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "♻️ *BioBot-ல் என்ன போடலாம்?*\n\n"
            "✅ *பச்சை (Nitrogen):*\n"
            "காய்கறி தோல், பழ கழிவு, காபி தூள்,\n"
            "முட்டை ஓடு, தேயிலை பை, புல்\n\n"
            "✅ *உலர்ந்தவை (Carbon):*\n"
            "கோகோபீட், பழைய செய்தித்தாள்,\n"
            "உலர்ந்த இலைகள், அட்டை\n\n"
            "❌ *ஒருபோதும் போடாதவை:*\n"
            "இறைச்சி, மீன், பால் பொருட்கள், எண்ணெய் உணவு,\n"
            "சமைத்த சோறு, பிளாஸ்டிக், உலோகம்\n\n"
            "📌 விகிதம்: 1 பங்கு பச்சை : 1 பங்கு உலர்ந்தவை",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "♻️ *What to Add to BioBot*\n\n"
            "✅ *GREENS (Nitrogen-rich):*\n"
            "Vegetable peels, fruit waste, coffee grounds,\n"
            "eggshells, tea bags, grass clippings\n\n"
            "✅ *BROWNS (Carbon-rich):*\n"
            "Cocopeat, shredded newspaper, dry leaves, cardboard\n\n"
            "❌ *NEVER ADD:*\n"
            "Meat, fish, dairy, oily food, cooked rice,\n"
            "pet waste, plastic, metal, glass\n\n"
            "📌 Ratio: 1 part greens : 1 part browns",
            parse_mode="Markdown"
        )

async def smell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "😷 *துர்நாற்றம் சரிசெய்வது எப்படி?*\n\n"
            "துர்நாற்றம் = காற்று இல்லாத நிலை!\n\n"
            "*வரிசையாக செய்யவும்:*\n"
            "1. லீச்சேட் தட்டை முழுவதும் காலி செய்யவும்\n"
            "2. மேலே உலர்ந்த கோகோபீட் அல்லது செய்தித்தாள் போடவும்\n"
            "3. Telegram அல்லது Blynk மூலம் கலக்கவும்\n"
            "4. இறைச்சி, பால் இருந்தால் உடனே எடுக்கவும்\n"
            "5. மூடியை 10 நிமிடம் திறந்து வைக்கவும்\n\n"
            "*வாசனை வகைகள்:*\n"
            "• 🌿 மண் வாசனை = ஆரோக்கியம் ✅\n"
            "• 💛 அம்மோனியா = உலர்ந்தவை சேர்க்கவும்\n"
            "• 🥚 அழுகிய முட்டை = ஈரம் அதிகம், கலக்கவும்\n"
            "• 🍬 இனிப்பு = பழம் அதிகம், உலர்ந்தவை சேர்க்கவும்",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "😷 *Fix Bad Odour*\n\n"
            "Bad smell = pile needs oxygen urgently!\n\n"
            "*Steps in order:*\n"
            "1. Drain the leachate tray completely\n"
            "2. Add dry cocopeat or shredded paper on top\n"
            "3. Trigger a mix via Telegram or Blynk\n"
            "4. Remove meat or dairy if present\n"
            "5. Open lid 10 minutes to ventilate\n\n"
            "*Smell types:*\n"
            "• 🌿 Earthy = healthy ✅\n"
            "• 💛 Ammonia = too much nitrogen — add browns\n"
            "• 🥚 Rotten egg = too wet — mix and drain\n"
            "• 🍬 Sweet = too much fruit — add dry material",
            parse_mode="Markdown"
        )

async def ready_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "🌱 *உரம் தயாரானதை எப்படி தெரிந்துகொள்வது?*\n\n"
            "அனைத்தும் YES ஆக இருக்க வேண்டும்:\n\n"
            "✅ நாள் 45 அல்லது அதிகம்\n"
            "✅ கருமை பழுப்பு அல்லது கருப்பு நிறம்\n"
            "✅ உதிரும் மண் போன்ற தன்மை\n"
            "✅ மண் வாசனை — அழுகல் இல்லாமல்\n"
            "✅ வெப்பநிலை 28-42C\n"
            "✅ வாயு 250 ADC-க்கு கீழ்\n"
            "✅ ஈரப்பதம் 40-60%\n\n"
            "அனைத்தும் சரி → harvest drawer திறந்து எடுக்கவும்! 🎉\n"
            "BioBot Telegram மூலம் தானாகவே தகவல் அனுப்பும்.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🌱 *How to Know Compost is Ready*\n\n"
            "All must be YES:\n\n"
            "✅ Day 45 or more\n"
            "✅ Dark brown to black colour\n"
            "✅ Crumbly and loose texture\n"
            "✅ Earthy forest soil smell\n"
            "✅ Temperature 28-42C\n"
            "✅ Gas below 250 ADC\n"
            "✅ Moisture 40-60%\n\n"
            "All yes → pull the BioBot harvest drawer! 🎉\n"
            "BioBot sends a Telegram alert automatically.",
            parse_mode="Markdown"
        )

async def leachate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "💧 *லீச்சேட் — கழிவு திரவம்*\n\n"
            "லீச்சேட் என்பது உரம் தயாரிக்கும் போது வெளியாகும் கழிவு திரவம்.\n"
            "BioBot-ன் அடிப்பகுதி slide-out தட்டில் சேகரமாகும்.\n\n"
            "⚠️ *இது உரமாக பயன்படுத்த கூடாது!*\n"
            "தீங்கான பாக்டீரியா மற்றும் அதிக அமிலம் இருக்கலாம்.\n\n"
            "*சரியான முறையில் கழிக்கவும்:*\n"
            "• 3-5 நாட்களுக்கு ஒருமுறை தட்டை காலி செய்யவும்\n"
            "• மண் குழியில் (உணவு பயிர்களுக்கு தொலைவில்) விடவும்\n"
            "• அல்லது கழிவு வடிகாலில் சேர்க்கவும்\n"
            "• உணவு பயிர்களில் நேரடியாக ஊற்றாதீர்கள்\n"
            "• தட்டில் தேங்கவிடாதீர்கள் — நாற்றம் மற்றும் பூச்சிகள் வரும்\n\n"
            "தொடர்ந்து கண்காணித்து சரியாக கழிக்கவும்! 🌿",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "💧 *Leachate — Waste Liquid Disposal*\n\n"
            "Leachate is the waste liquid produced during composting.\n"
            "It drains through the basket into BioBot's slide-out tray.\n\n"
            "⚠️ *It is NOT safe to use as fertiliser!*\n"
            "It may contain harmful bacteria and excessive acidity.\n\n"
            "*Dispose of it responsibly:*\n"
            "• Drain the tray every 3-5 days — never let it overflow\n"
            "• Pour into a soil pit away from edible plants\n"
            "• Or dispose into a municipal drain\n"
            "• Never pour directly onto vegetables or food crops\n"
            "• Overflow causes bad odour and attracts pests\n\n"
            "Regular disposal keeps BioBot clean and odour-free! 🌿",
            parse_mode="Markdown"
        )

async def sensors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if lang == "ta":
        await update.message.reply_text(
            "📡 *BioBot சென்சார் விளக்கம்*\n\n"
            "🌡️ *DHT22 — வெப்பநிலை மற்றும் ஈரப்பதம்*\n"
            "Basket-க்கும் drum-க்கும் இடையே உள்ள gap-ல் வைக்கப்படும்.\n"
            "சிறந்தது: 40-65C, 50-70% ஈரப்பதம்\n\n"
            "🌊 *Capacitive Moisture Sensor*\n"
            "உரம் குவியலின் ஈரப்பதம் அளவிடும்.\n"
            "சிறந்தது: 50-60%\n\n"
            "💨 *MQ-135 Gas Sensor*\n"
            "அம்மோனியா, CO2 கண்டறியும்.\n"
            "பாதுகாப்பு: 500 ADC கீழ் | ஆபத்து: 700 ADC மேல்\n\n"
            "🔆 *LDR Light Sensor*\n"
            "மூடி நிலை கண்டறியும்.\n"
            "🔴 Red = மூடி திறந்தது | 🟢 Green = மூடி மூடியது + ஆரோக்கியம்\n\n"
            "📅 *DS3231 RTC*\n"
            "மின் தடைப்பாடு இருந்தாலும் நாட்களை துல்லியமாக கணக்கிடும்.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "📡 *BioBot Sensor Guide*\n\n"
            "🌡️ *DHT22 — Temperature and Humidity*\n"
            "Placed in the aeration gap between basket and drum.\n"
            "Ideal: 40-65C temperature, 50-70% humidity\n\n"
            "🌊 *Capacitive Moisture Sensor*\n"
            "Measures compost pile moisture.\n"
            "Ideal: 50-60%\n\n"
            "💨 *MQ-135 Gas Sensor*\n"
            "Detects ammonia, CO2 and harmful gases.\n"
            "Safe: below 500 ADC | Danger: above 700 ADC\n\n"
            "🔆 *LDR Light Sensor*\n"
            "Detects if lid is open or closed.\n"
            "🔴 Red LED = lid open | 🟢 Green LED = lid closed + healthy\n\n"
            "📅 *DS3231 RTC*\n"
            "Tracks compost days accurately even during power cuts.",
            parse_mode="Markdown"
        )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_lang(uid)
    if uid in user_history:
        del user_history[uid]
    if lang == "ta":
        await update.message.reply_text("🔄 உரையாடல் அழிக்கப்பட்டது! மீண்டும் கேளுங்கள் 🌱")
    else:
        await update.message.reply_text("🔄 Conversation cleared! Fresh start 🌱")


# =====================================================
#  KEYBOARD BUTTON ROUTING
# =====================================================
BTN_EN = {
    "🌱 Tips":          tips_command,
    "📅 Stages":        stages_command,
    "♻️ What to Add":  add_command,
    "😷 Fix Smell":     smell_command,
    "✅ Is it Ready?":  ready_command,
    "💧 Leachate":      leachate_command,
    "📡 Sensors":       sensors_command,
    "🌿 About BioBot":  about_command,
}
BTN_TA = {
    "🌱 குறிப்புகள்":      tips_command,
    "📅 நிலைகள்":          stages_command,
    "♻️ என்ன போடலாம்":   add_command,
    "😷 நாற்றம் சரிசெய்": smell_command,
    "✅ உரம் தயாரா?":      ready_command,
    "💧 லீச்சேட்":          leachate_command,
    "📡 சென்சார்கள்":      sensors_command,
    "🌿 BioBot பற்றி":     about_command,
}

# =====================================================
#  MAIN MESSAGE HANDLER
# =====================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    text = update.message.text.strip()
    name = update.effective_user.first_name or "User"
    lang = get_lang(uid)

    if not text:
        return

    logger.info(f"Message from {name} (ID:{uid}) [{lang}]: {text[:80]}")

    # Language switch buttons
    if text == "🇮🇳 தமிழில் பேசு":
        await tamil_command(update, context)
        return
    if text == "🇬🇧 Switch to English":
        await english_command(update, context)
        return

    # Keyboard buttons
    btn_map = BTN_TA if lang == "ta" else BTN_EN
    if text in btn_map:
        await btn_map[text](update, context)
        return

    # Free text → Groq AI
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await ask_groq(uid, text, lang)
    try:
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(reply)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Telegram error: {context.error}")

# =====================================================
#  MAIN ENTRY POINT
# =====================================================
def main():
    print("=" * 55)
    print("  BioBot Telegram AI Chatbot — GROQ VERSION")
    print("  Language: English + Tamil (தமிழ்)")
    print("  Anna University, Tiruchirappalli")
    print(f"  AI Model : {GROQ_MODEL}")
    print(f"  Token    : {'SET' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
    print(f"  Groq Key : {'SET' if GROQ_API_KEY else 'MISSING'}")
    print("=" * 55)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    start_command))
    app.add_handler(CommandHandler("help",     help_command))
    app.add_handler(CommandHandler("about",    about_command))
    app.add_handler(CommandHandler("tips",     tips_command))
    app.add_handler(CommandHandler("stages",   stages_command))
    app.add_handler(CommandHandler("add",      add_command))
    app.add_handler(CommandHandler("smell",    smell_command))
    app.add_handler(CommandHandler("ready",    ready_command))
    app.add_handler(CommandHandler("leachate", leachate_command))
    app.add_handler(CommandHandler("sensors",  sensors_command))
    app.add_handler(CommandHandler("reset",    reset_command))
    app.add_handler(CommandHandler("tamil",    tamil_command))
    app.add_handler(CommandHandler("english",  english_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("  BioBot is running! Waiting for messages...")
    print("=" * 55)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
