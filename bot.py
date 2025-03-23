# bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import logging
import asyncio
import sys
from database import SessionLocal, engine, Base
from models import User
Base.metadata.create_all(bind=engine)
print("[DEBUG] All tables created (if they did not exist already).")


# Force UTF-8 encoding (Windows Fix)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to remember user's last mode (Mini App or Regular Bot)
USER_SESSIONS = {}

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📄 Open Mini App", web_app=WebAppInfo(url="https://a5ec-77-91-70-239.ngrok-free.app"))],
        [InlineKeyboardButton("📄 Buy eSIM", callback_data="buy_esim")],
        [InlineKeyboardButton("🔑 My eSIMs", callback_data="my_esims")],
        [InlineKeyboardButton("💬 Support", url="https://t.me/esim_unlimited_support_bot"),
         InlineKeyboardButton("📌 Guides", callback_data="guides")],
        [InlineKeyboardButton("🆕 Project News", url="https://t.me/eSIM_Unlimited"),
         InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("🎁 Activate Promo Code", callback_data="promo"),
         InlineKeyboardButton("🔗 Referral System", callback_data="referral")]
    ]
    return InlineKeyboardMarkup(keyboard)

def store_user_in_db(telegram_user):
    """
    Store or update user data in the PostgreSQL database.
    telegram_user is an instance of telegram.User (from update.message.from_user).
    """
    db = SessionLocal()
    try:
        telegram_id = str(telegram_user.id)
        # Check if the user already exists
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        # Use first_name as a fallback if username is not provided
        username = telegram_user.username or telegram_user.first_name or "Telegram User"
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                photo_url=None  # telegram.User doesn't have photo_url; mini app auth can update this later
            )
            db.add(user)
            print(f"[BOT DEBUG] New user created: {telegram_id} - {username}")
        else:
            # Update the username in case it has changed
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
    
    # Store or update the user info in DB from /start command
    store_user_in_db(update.message.from_user)
    
    # Record the user's mode (for this example, defaulting to "regular")
    USER_SESSIONS[user_id] = "regular"
    
    last_mode = USER_SESSIONS.get(user_id, "regular")
    if last_mode == "mini_app":
        await update.message.reply_text("🖥️ Opening Mini App...", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url="https://a5ec-77-91-70-239.ngrok-free.app"))]
        ]))
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
        await query.message.reply_text("🔑 Listing your eSIMs...")  # Fetch from database
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

async def set_bot_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Show the main menu"),
        BotCommand("miniapp", "Show the main menu"),
        BotCommand("menu", "Show the main menu"),
        BotCommand("buy", "Buy an eSIM"),
        BotCommand("myesims", "View your eSIMs"),
        BotCommand("topup", "Top-up an eSIM"),
        BotCommand("cancel", "Cancel an eSIM"),
        BotCommand("promocode", "Activate a promo code"),
        BotCommand("settings", "Manage bot settings"),
        BotCommand("support", "Contact support"),
        BotCommand("guides", "Open guides"),
        BotCommand("faq", "View FAQ"),
        BotCommand("news", "Get project news"),
        BotCommand("referral", "Referral system")
    ], language_code="en")

if __name__ == "__main__":
    import sys
    from telegram.ext import Application
    from telegram.ext import CommandHandler, CallbackQueryHandler
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    application = Application.builder().token("8073824494:AAHQlUVQpvlzBFX_5kfjD02tcdRkjGTGBeI").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    asyncio.get_event_loop().run_until_complete(set_bot_commands(application))
    application.run_polling()
