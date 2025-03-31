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

# Try to import Request for custom timeout; fallback if unavailable.
try:
    from telegram.utils.request import Request
    custom_request_available = True
except ImportError:
    custom_request_available = False

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
SUPPORT_BOT = os.getenv("SUPPORT_BOT")
NEWS_CHANNEL = os.getenv("NEWS_CHANNEL")
WEBAPP_FAQ_URL = os.getenv("WEBAPP_FAQ_URL")
WEBAPP_GUIDES_URL = os.getenv("WEBAPP_GUIDES_URL")

# ====== 1) Load list of countries ======
try:
    with open("public/countries.json", encoding="utf-8") as f:
        countries_data = json.load(f)
    COUNTRIES = [{"code": code, "name": name} for code, name in countries_data.items()]
except Exception as e:
    print("[BOT DEBUG] Error loading countries.json:", e)
    COUNTRIES = []

# ====== 2) Load countryPackages.json ======
try:
    with open("public/countryPackages.json", "r", encoding="utf-8") as f:
        all_country_packages = json.load(f)
except Exception as e:
    print("[BOT DEBUG] Error loading countryPackages.json:", e)
    all_country_packages = []

# Build set of country codes with available packages
COUNTRY_CODES_WITH_PACKAGES = set(pkg.get("location") for pkg in all_country_packages)

# ====== 3) Load regionalPackages.json ======
try:
    with open("public/regionalPackages.json", "r", encoding="utf-8") as f:
        all_regional_packages = json.load(f)
except Exception as e:
    print("[BOT DEBUG] Error loading regionalPackages.json:", e)
    all_regional_packages = []

# ====== 4) Define REGION_ICONS mapping without PNG file paths ======
# Telegram bot buttons cannot display images, so we keep only the predicate functions.
REGION_ICONS = {
    "Europe": lambda pkg: "Europe" in pkg.get("name", ""),
    "South America": lambda pkg: "South America" in pkg.get("name", ""),
    "North America": lambda pkg: "North America" in pkg.get("name", ""),
    "Africa": lambda pkg: "Africa" in pkg.get("name", ""),
    "Asia (excl. China)": lambda pkg: ("Asia" in pkg.get("name", "") or
                         "Singapore" in pkg.get("name", "")), 
    "China": lambda pkg: ("China" in pkg.get("name", "")),
    "Gulf": lambda pkg: "Gulf" in pkg.get("name", ""),
    "Middle East": lambda pkg: "Middle East" in pkg.get("name", ""),
    "Caribbean": lambda pkg: "Caribbean" in pkg.get("name", "")
}

# ====== 5) Load globalPackages.json and define Global Package Types ======
try:
    with open("public/globalPackages.json", "r", encoding="utf-8") as f:
        all_global_packages = json.load(f)
except Exception as e:
    print("[BOT DEBUG] Error loading globalPackages.json:", e)
    all_global_packages = []

GLOBAL_PACKAGE_TYPES = {
    "Global 1GB": 1,
    "Global 3GB": 3,
    "Global 5GB": 5,
    "Global 10GB": 10,
    "Global 20GB": 20,
}

Base.metadata.create_all(bind=engine)
print("[DEBUG] All tables created (if they did not exist already).")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

USER_SESSIONS = {}

# --- Helper: Build paginated inline keyboard for package buttons ---
def build_paginated_keyboard(button_rows, page, rows_per_page=10):
    total_pages = (len(button_rows) - 1) // rows_per_page + 1
    start = page * rows_per_page
    end = start + rows_per_page
    current_buttons = button_rows[start:end]
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("Previous", callback_data=f"page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next", callback_data=f"page_{page+1}"))
    if nav_buttons:
        current_buttons.append(nav_buttons)
    return InlineKeyboardMarkup(current_buttons)

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
            user = User(telegram_id=telegram_id, username=username, photo_url=None)
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

    # If awaiting country search (for local packages)
    if context.chat_data.get("awaiting_country_search"):
        query = text.lower()
        matching = [
            c for c in COUNTRIES
            if query in c["name"].lower() and c["code"] in COUNTRY_CODES_WITH_PACKAGES
        ]
        if not matching:
            await update.message.reply_text("No matching countries with packages found. Please try again.")
        else:
            keyboard = []
            for country in matching:
                flag = country_code_to_emoji(country["code"])
                button_text = f"{flag} {country['name']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"local_{country['code']}")])
            inline_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Select a country:", reply_markup=inline_markup)
        context.chat_data["awaiting_country_search"] = False
        return

    # Standard message processing
    if text == "🖥️ Open Mini App":
        web_app_button = InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url=WEBAPP_URL))
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
        filtered_packages = [pkg for pkg in all_country_packages if pkg.get("location") == country_code]
        if not filtered_packages:
            await query.message.reply_text(f"No packages available for {country_flag} {country_name}.")
            return
        filtered_packages.sort(key=lambda p: p.get("retailPrice", 0))
        table_header = (
            "```\n"
            "Volume   | Duration | Price   | Top-Up\n"
            "---------|----------|---------|-------\n"
        )
        table_rows = []
        keyboard_rows = []
        for pkg in filtered_packages:
            volume_gb = round(pkg.get("volume", 0) / (1024 * 1024 * 1024), 1)
            duration = pkg.get("duration", "N/A")
            price = pkg.get("retailPrice", 0) / 10000
            name = pkg.get("name", "N/A")
            support = "Yes" if pkg.get("supportTopUpType", 0) == 2 else "No"
            support_emoji = "✅" if support == "Yes" else "❌"
            package_code = pkg.get("packageCode", "N/A")
            row_str = f"{volume_gb:>6.1f}GB | {duration:>7}d | ${price:>6.2f} | {support:>5}"
            table_rows.append(row_str)
            btn_text = f"More Info {name}   ${price:.2f}"
            keyboard_rows.append([InlineKeyboardButton(btn_text, callback_data=f"moreinfo_{package_code}")])
        table_body = "\n".join(table_rows)
        table_footer = "\n```"
        table_message = (
            f"Available packages for {country_flag} {country_name}:\n\n"
            f"{table_header}{table_body}{table_footer}\n\n"
            "Select a package:"
        )
        inline_markup = InlineKeyboardMarkup(keyboard_rows)
        await query.message.reply_text(table_message, parse_mode="Markdown", reply_markup=inline_markup)

    elif data == "buy_regional":
        regions = list(REGION_ICONS.keys())
        num_cols = 3  # Set number of columns per row
        keyboard = [
            [InlineKeyboardButton(region, callback_data=f"regional_{region}") 
             for region in regions[i:i+num_cols]]
            for i in range(0, len(regions), num_cols)
        ]
        inline_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select a region:", reply_markup=inline_markup)

    elif data.startswith("regional_"):
        region = data.split("_", 1)[1]
        if region not in REGION_ICONS:
            await query.message.reply_text("Region not recognized.")
            return
        predicate = REGION_ICONS[region]
        filtered_packages = [pkg for pkg in all_regional_packages if predicate(pkg)]
        if not filtered_packages:
            await query.message.reply_text(f"No regional packages available for {region}.")
            return
        filtered_packages.sort(key=lambda p: p.get("retailPrice", 0))
        table_header = (
            "```\n"
            " Vol    Dur    Price  Top-Up  # Countries\n"
            "-----------------------------------------\n"
        )
        table_rows = []
        keyboard_rows = []
        for pkg in filtered_packages:
            volume_gb = round(pkg.get("volume", 0) / (1024 * 1024 * 1024), 1)
            duration = pkg.get("duration", "N/A")
            duration_display = str(duration) + "d"
            price = pkg.get("retailPrice", 0) / 10000
            name = pkg.get("name", "N/A")
            support = "Yes" if pkg.get("supportTopUpType", 0) == 2 else "No"
            support_emoji = "✅" if support == "Yes" else "❌"
            coverage = len(pkg.get("locationNetworkList", []))
            row_str = f"{volume_gb:>4.1f}GB| {duration_display:^4}| ${price:^7.2f}|{support_emoji:^3}| {coverage:^10}"
            table_rows.append(row_str)
            btn_text = f"More Info {name}   ${price:.2f}"
            keyboard_rows.append([InlineKeyboardButton(btn_text, callback_data=f"moreinfo_{pkg.get('packageCode', 'N/A')}")])
        table_body = "\n".join(table_rows)
        table_footer = "\n```"
        full_table_text = (
            f"Available regional packages for {region}:\n\n"
            f"{table_header}{table_body}{table_footer}\n\n"
            "Select a package:"
        )
        # Store the full table text and button list in chat_data for pagination callbacks.
        context.chat_data["current_table_text"] = full_table_text
        context.chat_data["current_button_rows"] = keyboard_rows
        context.chat_data["current_page"] = 0

        # Build initial paginated inline keyboard for page 0.
        initial_markup = build_paginated_keyboard(keyboard_rows, page=0)
        await query.message.reply_text(full_table_text, parse_mode="Markdown", reply_markup=initial_markup)

    elif data.startswith("globalcat_"):
        try:
            category_value = int(data.split("_", 1)[1])
        except ValueError:
            await query.message.reply_text("Invalid category.")
            return
        filtered_packages = [pkg for pkg in all_global_packages if int(round(pkg.get("volume", 0) / (1024*1024*1024))) == category_value]
        if not filtered_packages:
            await query.message.reply_text(f"No global packages available for {category_value}GB.")
            return
        filtered_packages.sort(key=lambda p: p.get("retailPrice", 0))
        table_header = (
            "```\n"
            " Vol    Dur    Price  Top-Up  # Countries\n"
            "-----------------------------------------\n"
        )
        table_rows = []
        keyboard_rows = []
        for pkg in filtered_packages:
            volume_gb = round(pkg.get("volume", 0) / (1024*1024*1024), 1)
            duration = pkg.get("duration", "N/A")
            duration_display = str(duration) + "d"
            price = pkg.get("retailPrice", 0) / 10000
            name = pkg.get("name", "N/A")
            support = "Yes" if pkg.get("supportTopUpType", 0) == 2 else "No"
            support_emoji = "✅" if support == "Yes" else "❌"
            coverage = len(pkg.get("locationNetworkList", []))
            row_str = f"{volume_gb:>4.1f}GB| {duration_display:^4}| ${price:^7.2f}|{support_emoji:^3}| {coverage:^10}"
            table_rows.append(row_str)
            btn_text = f"More Info {name}   ${price:.2f}"
            keyboard_rows.append([InlineKeyboardButton(btn_text, callback_data=f"moreinfo_{pkg.get('packageCode', 'N/A')}")])
        table_body = "\n".join(table_rows)
        table_footer = "\n```"
        full_table_text = (
            f"Available global packages for {category_value}GB:\n\n"
            f"{table_header}{table_body}{table_footer}\n\n"
            "Select a package:"
        )
        context.chat_data["current_table_text"] = full_table_text
        context.chat_data["current_button_rows"] = keyboard_rows
        context.chat_data["current_page"] = 0
        initial_markup = build_paginated_keyboard(keyboard_rows, page=0)
        await query.message.reply_text(full_table_text, parse_mode="Markdown", reply_markup=initial_markup)

    elif data == "buy_global":
        # Show Global categories first.
        categories = list(GLOBAL_PACKAGE_TYPES.keys())
        num_cols = 2  # Adjust as needed.
        keyboard = [
            [InlineKeyboardButton(cat, callback_data=f"globalcat_{GLOBAL_PACKAGE_TYPES[cat]}") for cat in categories[i:i+num_cols]]
            for i in range(0, len(categories), num_cols)
        ]
        inline_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select a global package category:", reply_markup=inline_markup)

    elif data.startswith("page_"):
        # Handle pagination navigation for regional/global package buttons.
        page = int(data.split("_", 1)[1])
        table_text = context.chat_data.get("current_table_text")
        button_rows = context.chat_data.get("current_button_rows")
        if table_text and button_rows is not None:
            new_markup = build_paginated_keyboard(button_rows, page)
            await query.message.edit_reply_markup(reply_markup=new_markup)
            context.chat_data["current_page"] = page

    elif data.startswith("moreinfo_"):
        package_code = data.split("_", 1)[1]
        # Search for the package in local, regional and global lists.
        pkg = next((p for p in all_country_packages if p.get("packageCode") == package_code), None)
        if pkg is None:
            pkg = next((p for p in all_regional_packages if p.get("packageCode") == package_code), None)
        if pkg is None:
            pkg = next((p for p in all_global_packages if p.get("packageCode") == package_code), None)
        if pkg is None:
            await query.message.reply_text("Package not found.")
            return
        volume_gb = round(pkg.get("volume", 0) / (1024 * 1024 * 1024), 1)
        duration = pkg.get("duration", "N/A")
        price = pkg.get("retailPrice", 0) / 10000
        name = pkg.get("name", "N/A")
        support = "✅" if pkg.get("supportTopUpType", 0) == 2 else "❌"
        coverage = len(pkg.get("locationNetworkList", []))
        supported_countries = [ln.get("locationName", "") for ln in pkg.get("locationNetworkList", [])]
        supported_countries_str = ", ".join(supported_countries) if supported_countries else "N/A"
        detailed_message = (
            f"<b>Name:</b> {name}\n"
            f"<b>Data Volume:</b> {volume_gb}GB\n"
            f"<b>Duration:</b> {duration} days\n"
            f"<b>Price:</b> <i><b>💲{price:.2f}</b></i>\n"
            f"<b>Top-Up:</b> {support}\n"
            f"<b>Coverage:</b> {coverage} Countries\n"
            f"<b>Supported Countries:</b> {supported_countries_str}"
        )
        buy_button = InlineKeyboardButton("Buy", callback_data=f"buypkg_{package_code}")
        keyboard = InlineKeyboardMarkup([[buy_button]])
        await query.message.reply_text(
                detailed_message,
                parse_mode="HTML",
                reply_markup=keyboard
            )

    elif data.startswith("buypkg_"):
        package_code = data.split("_", 1)[1]
        await query.message.reply_text(f"You selected package {package_code} for purchase (not implemented).")

async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    if custom_request_available:
        req = Request(connect_timeout=600)  # Increased timeout value
        application = Application.builder().token(TELEGRAM_TOKEN).request(req).build()
    else:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    application.run_polling()
