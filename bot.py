# bot.py
import sys
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters
import os
from dotenv import load_dotenv

load_dotenv()  # Загрузит переменные из .env

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# Импорт работы с базой данных и моделями
from database import SessionLocal, engine, Base
from models import User

Base.metadata.create_all(bind=engine)
print("[DEBUG] All tables created (if they did not exist already).")

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальное хранилище пользовательских сессий
USER_SESSIONS = {}

# ================================
# Клавиатуры и обработчики сообщений
# ================================

def main_menu_keyboard():
    keyboard = [
        ["📄 Open Mini App"],
        ["📄 Buy eSIM", "🔑 My eSIMs"],
        ["❓ FAQ", "📌 Guides"],
        ["🆕 Project News", "💬 Support"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "📄 Open Mini App":
        web_app_button = InlineKeyboardButton(
            "Open Mini App",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
        keyboard = InlineKeyboardMarkup([[web_app_button]])
        await update.message.reply_text("Click below to open the Mini App:", reply_markup=keyboard)
    # Добавьте обработку других сообщений при необходимости...

def store_user_in_db(telegram_user):
    db = SessionLocal()
    try:
        telegram_id = str(telegram_user.id)
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        username = telegram_user.username or telegram_user.first_name or "Telegram User"
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                photo_url=None  # Здесь можно обновлять photo_url, если понадобится
            )
            db.add(user)
            print(f"[BOT DEBUG] New user created: {telegram_id} - {username}")
        else:
            user.username = username
            print(f"[BOT DEBUG] Existing user updated: {telegram_id} - {username}")
        db.commit()
    except Exception as e:
        print("[BOT DEBUG] Error storing user in DB:", e)
        db.rollback()
    finally:
        db.close()

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    logger.info(f"User {user_id} started the bot.")
    store_user_in_db(update.message.from_user)
    USER_SESSIONS[user_id] = "regular"
    last_mode = USER_SESSIONS.get(user_id, "regular")
    if last_mode == "mini_app":
        await update.message.reply_text(
            "🖥️ Opening Mini App...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url=WEBAPP_URL))]
            ])
        )
    else:
        await update.message.reply_text("Welcome! Choose an option:", reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.message.chat_id
    if data == "buy_esim":
        await query.message.reply_text("📄 Choose your eSIM plan:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Local", callback_data="buy_local"), InlineKeyboardButton("Regional", callback_data="buy_regional")],
            [InlineKeyboardButton("Global", callback_data="buy_global")]
        ]))
    elif data == "my_esims":
        await query.message.reply_text("🔑 Listing your eSIMs...")
    elif data == "guides":
        await query.message.reply_text("📌 Opening Guides in Mini App...", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Guides", web_app=WebAppInfo(url="https://your-mini-app-url.com/guides"))]
        ]))
    elif data == "faq":
        await query.message.reply_text("❓ Opening FAQ in Mini App...", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Open FAQ", web_app=WebAppInfo(url="https://your-mini-app-url.com/faq"))]
        ]))
    elif data == "promo":
        await query.message.reply_text("🎁 Enter your promo code using /promocode [code]")
    elif data == "referral":
        await query.message.reply_text("🔗 Invite friends and earn rewards!")

# ================================
# Основной блок и запуск бота
# ================================

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()
