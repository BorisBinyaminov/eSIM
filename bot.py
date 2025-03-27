# bot.py
import sys
import logging
import asyncio
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from database import SessionLocal, engine, Base
from models import User

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
SUPPORT_BOT = os.getenv("SUPPORT_BOT")
NEWS_CHANNEL = os.getenv("NEWS_CHANNEL")
WEBAPP_FAQ_URL = os.getenv("WEBAPP_FAQ_URL")
WEBAPP_GUIDES_URL = os.getenv("WEBAPP_GUIDES_URL")

# ====== 1) Загрузка списка стран  ======
try:
    with open("public/countries.json", encoding="utf-8") as f:
        countries_data = json.load(f)
    COUNTRIES = [{"code": code, "name": name} for code, name in countries_data.items()]
except Exception as e:
    print("[BOT DEBUG] Error loading countries.json:", e)
    COUNTRIES = []

# ====== 2) Загрузка countryPackages.json ======
try:
    with open("public/countryPackages.json", "r", encoding="utf-8") as f:
        all_country_packages = json.load(f)
except Exception as e:
    print("[BOT DEBUG] Error loading countryPackages.json:", e)
    all_country_packages = []

# Формируем множество кодов стран, у которых есть пакеты
COUNTRY_CODES_WITH_PACKAGES = set(pkg.get("location") for pkg in all_country_packages)

Base.metadata.create_all(bind=engine)
print("[DEBUG] All tables created (if they did not exist already).")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

USER_SESSIONS = {}

def main_menu_keyboard():
    keyboard = [
        ["🖥️ Open Mini App"],
        ["🛒 Buy eSIM", "🔑 My eSIMs"],
        ["❓ FAQ", "📌 Guides"],
        ["🆕 Project News", "💬 Support"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def buy_esim_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Local", callback_data="buy_local"),
            InlineKeyboardButton("Regional", callback_data="buy_regional"),
            InlineKeyboardButton("Global", callback_data="buy_global")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def country_code_to_emoji(country_code: str) -> str:
    """Convert a 2-letter country code to a flag emoji."""
    if len(country_code) != 2:
        return ""
    offset = 127397
    return chr(ord(country_code[0].upper()) + offset) + chr(ord(country_code[1].upper()) + offset)

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
                photo_url=None
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
    await update.message.reply_text("Welcome to eSIM Unlimited! Choose an option:", reply_markup=main_menu_keyboard())

async def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text

    # Если ждём поиска страны
    if context.chat_data.get("awaiting_country_search"):
        query = text.lower()

        # Фильтруем страны: ищем совпадение по названию И проверяем, есть ли пакеты
        matching = [
            c for c in COUNTRIES
            if query in c["name"].lower()
               and c["code"] in COUNTRY_CODES_WITH_PACKAGES
        ]
        if not matching:
            await update.message.reply_text("No matching countries with packages found. Please try again.")
        else:
            # Строим inline-клавиатуру
            keyboard = []
            for country in matching:
                flag = country_code_to_emoji(country["code"])
                button_text = f"{flag} {country['name']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"local_{country['code']}")])
            inline_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Select a country:", reply_markup=inline_markup)

        context.chat_data["awaiting_country_search"] = False
        return

    # Иначе - стандартная обработка
    if text == "🖥️ Open Mini App":
        web_app_button = InlineKeyboardButton(
            "Open Mini App",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
        keyboard = InlineKeyboardMarkup([[web_app_button]])
        await update.message.reply_text("Click below to open the Mini App:", reply_markup=keyboard)
    
    elif text == "💬 Support":
        support_button = InlineKeyboardButton("Click for Support", url=SUPPORT_BOT)
        keyboard = InlineKeyboardMarkup([[support_button]])
        await update.message.reply_text("Click here to open the Support chat:", reply_markup=keyboard)
    
    elif text == "🆕 Project News":
        news_button = InlineKeyboardButton("Click for Project News", url=NEWS_CHANNEL)
        keyboard = InlineKeyboardMarkup([[news_button]])
        await update.message.reply_text("Click here to open our News Channel:", reply_markup=keyboard)
    
    elif text == "❓ FAQ":
        faq_button = InlineKeyboardButton("Open FAQ", url=WEBAPP_FAQ_URL)
        keyboard = InlineKeyboardMarkup([[faq_button]])
        await update.message.reply_text("Click here to open FAQ:", reply_markup=keyboard)
    
    elif text == "📌 Guides":
        guides_button = InlineKeyboardButton("Open Guides", url=WEBAPP_GUIDES_URL)
        keyboard = InlineKeyboardMarkup([[guides_button]])
        await update.message.reply_text("Click here to open Guides:", reply_markup=keyboard)
    
    elif text == "🛒 Buy eSIM":
        await update.message.reply_text("Choose your eSIM plan:", reply_markup=buy_esim_keyboard())

async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "buy_local":
        # Спросим у пользователя часть названия страны
        await query.message.reply_text("Please enter a country name (or part of it) to search:")
        context.chat_data["awaiting_country_search"] = True

    elif data.startswith("local_"):
        country_code = data.split("_", 1)[1]
        country = next((c for c in COUNTRIES if c["code"] == country_code), None)
        if not country:
            await query.message.reply_text("Country not found in the list.")
            return

        country_name = country["name"]
        country_flag = country_code_to_emoji(country_code)

        # Фильтруем пакеты для конкретной страны из all_country_packages
        filtered_packages = [pkg for pkg in all_country_packages if pkg.get("location") == country_code]
        if not filtered_packages:
            await query.message.reply_text(f"No packages available for {country_flag} {country_name}.")
            return

        # Сортируем по цене
        filtered_packages.sort(key=lambda p: p.get("retailPrice", 0))

        # Формируем ASCII-таблицу (Markdown)
        table_header = (
        f"```\n"
        " Volume        Duration      Price    Top-Up\n"
        "-------        --------      -----    ------\n"
        )
        table_rows = []
        keyboard_rows = []

        for pkg in filtered_packages:
            volume_gb = pkg.get("volume", 0) / (1024 * 1024 * 1024)
            volume_gb = round(volume_gb, 1)
            duration = pkg.get("duration", "N/A")
            price = pkg.get("retailPrice", 0) / 10000
            support = "Yes" if pkg.get("supportTopUpType", 0) == 2 else "No"
            package_code = pkg.get("packageCode", "N/A")

            row_str = f"{volume_gb:>5.1f}GB     | {duration:>5}d      | ${price:>6.2f} | {support:>5}"
            table_rows.append(row_str)

            # Кнопка для покупки
            btn_text = f"{volume_gb}GB, {duration}d, ${price:.2f}, {support}"
            keyboard_rows.append([InlineKeyboardButton(btn_text, callback_data=f"buypkg_{package_code}")])

        table_body = "\n".join(table_rows)
        table_footer = "```"

        table_message = (
            f"Available packages for {country_flag} {country_name}:\n\n"
            f"{table_header}{table_body}\n{table_footer}\n\n"
            "Select a package:"
        )

        inline_markup = InlineKeyboardMarkup(keyboard_rows)

        await query.message.reply_text(
            table_message,
            parse_mode="Markdown",
            reply_markup=inline_markup
        )

    elif data == "buy_regional":
        await query.message.reply_text("You selected Regional eSIM packages.")
        # ...
    elif data == "buy_global":
        await query.message.reply_text("You selected Global eSIM packages.")
        # ...
    elif data.startswith("buypkg_"):
        # Обработка покупки пакета
        package_code = data.split("_", 1)[1]
        await query.message.reply_text(f"You selected package {package_code} for purchase (not implemented).")
    # ... другие ветки ...

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()
