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
import buy_esim
from models import Order
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

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
REGION_ICONS = {
    "Europe": lambda pkg: "Europe" in pkg.get("name", ""),
    "South America": lambda pkg: "South America" in pkg.get("name", ""),
    "North America": lambda pkg: "North America" in pkg.get("name", ""),
    "Africa": lambda pkg: "Africa" in pkg.get("name", ""),
    "Asia (excl. China)": lambda pkg: ("Asia" in pkg.get("name", "") or "Singapore" in pkg.get("name", "")),
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

#Base.metadata.drop_all(bind=engine)
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
    def sort_esims_priority(esim_data):
        def get_priority(entry):
            status = entry["data"].get("esimStatus", "")
            smdp = entry["data"].get("smdpStatus", "")
            if smdp == "RELEASED" and status == "GOT_RESOURCE":
                return 0  # New
            elif smdp == "ENABLED" and status == "IN_USE":
                return 1  # In Use
            elif smdp == "ENABLED" and status == "GOT_RESOURCE":
                return 2  # Onboard
            elif status == "USED_UP":
                return 3  # Depleted
            elif status == "DELETED":
                return 4  # Deleted
            else:
                return 5  # Unknown or less relevant

        return sorted(esim_data, key=get_priority)

    if "pending_purchase" in context.chat_data:
        try:
            quantity = int(text.strip())
            if quantity <= 0:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("Please enter a valid positive number.")
            return

        purchase = context.chat_data.pop("pending_purchase")
        try:
            result = await buy_esim.process_purchase(
                package_code=purchase["package_code"],
                user_id=str(update.effective_user.id),
                order_price=purchase["order_price"],
                retail_price=purchase["retail_price"],
                count=1 if purchase["duration"] == 1 else quantity,
                period_num=quantity if purchase["duration"] == 1 else None
            )
            qr_codes = result.get("qrCodes")
            if isinstance(qr_codes, list) and len(qr_codes) > 1:
                await update.message.reply_text(f"✅ You purchased {len(qr_codes)} eSIMs. Here are your QR codes:")
                for idx, qr in enumerate(qr_codes, 1):
                    await update.message.reply_text(f"eSIM #{idx}:\n{qr}")
            elif qr_codes:
                await update.message.reply_text(f"✅ Purchase successful! Your QR code:\n{qr_codes[0]}")
            else:
                await update.message.reply_text("✅ Purchase completed, but no QR code was returned.")
        except Exception as e:
            import traceback
            import html
            error_msg = html.escape(traceback.format_exc())
            await update.message.reply_text(f"❌ Error:\n<code>{error_msg}</code>", parse_mode="HTML")
        return

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
    elif text == "🔑 My eSIMs":
        await update.message.reply_text("🔍 Checking your eSIMs... This may take a few seconds ⏳")
        esim_data = await buy_esim.my_esim(str(update.effective_user.id))
        if not esim_data:
            await update.message.reply_text("You have no eSIMs yet.")
            return
        session = SessionLocal()
        esim_data = sort_esims_priority(esim_data)
        for entry in esim_data:
            iccid = entry["iccid"]
            api_data = entry["data"]
            db_entry = session.query(Order).filter(Order.iccid == iccid).first()
            update_usage_by_iccid(session, iccid, api_data)
            text = format_esim_info(api_data, db_entry)

            buttons = []

            # ❌ Показать "Cancel", если eSIM не установлена и активна
            if api_data.get("smdpStatus") == "RELEASED" and api_data.get("esimStatus") == "GOT_RESOURCE":
                buttons.append(InlineKeyboardButton("❌ Cancel", callback_data=f"precancel_{iccid}"))

            # ✅ Показать "Top-Up", если:
            # 1. В профиле указано supportTopUpType == 2
            # 2. Актуальный статус eSIM допускает пополнение
            try:
                esim_list = json.loads(db_entry.esim_list)
                support_topup = esim_list[0].get("supportTopUpType", 0)

                # Состояния eSIM, при которых разрешён Top-Up:
                allowed_status = (
                    api_data.get("smdpStatus") in ["RELEASED", "ENABLED"] and
                    api_data.get("esimStatus") in ["GOT_RESOURCE", "IN_USE"]
                )

                if support_topup == 2 and allowed_status:
                    buttons.append(InlineKeyboardButton("➕ Top-up", callback_data=f"topup_{iccid}"))

            except Exception as e:
                logger.warning(f"Failed to parse supportTopUpType or status: {e}")

            buttons.append(InlineKeyboardButton("🔄 Refresh Usage", callback_data=f"refresh_{iccid}"))
            keyboard = InlineKeyboardMarkup([buttons]) if buttons else None


            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )

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
            btn_text = f"More Info on {name}   ${price:.2f}"
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
        num_cols = 3
        keyboard = [
            [InlineKeyboardButton(region, callback_data=f"regional_{region}") for region in regions[i:i+num_cols]]
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
            btn_text = f"More Info on {name}   ${price:.2f}"
            keyboard_rows.append([InlineKeyboardButton(btn_text, callback_data=f"moreinfo_{pkg.get('packageCode', 'N/A')}")])
        table_body = "\n".join(table_rows)
        table_footer = "\n```"
        full_table_text = (
            f"Available regional packages for {region}:\n\n"
            f"{table_header}{table_body}{table_footer}\n\n"
            "Select a package:"
        )
        context.chat_data["current_table_text"] = full_table_text
        context.chat_data["current_button_rows"] = keyboard_rows
        context.chat_data["current_page"] = 0
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
            btn_text = f"More Info on {name}   ${price:.2f}"
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
        categories = list(GLOBAL_PACKAGE_TYPES.keys())
        num_cols = 2
        keyboard = [
            [InlineKeyboardButton(cat, callback_data=f"globalcat_{GLOBAL_PACKAGE_TYPES[cat]}") for cat in categories[i:i+num_cols]]
            for i in range(0, len(categories), num_cols)
        ]
        inline_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select a global package category:", reply_markup=inline_markup)

    elif data.startswith("page_"):
        page = int(data.split("_", 1)[1])
        table_text = context.chat_data.get("current_table_text")
        button_rows = context.chat_data.get("current_button_rows")
        if table_text and button_rows is not None:
            new_markup = build_paginated_keyboard(button_rows, page)
            await query.message.edit_reply_markup(reply_markup=new_markup)
            context.chat_data["current_page"] = page

    elif data.startswith("moreinfo_"):
        package_code = data.split("_", 1)[1]
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
            f"<b>Price:</b> <i><b>${price:.2f}</b></i>\n"
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
        user_id = str(update.effective_user.id)

        # Find the selected package
        package = next((p for p in all_country_packages if p.get("packageCode") == package_code), None)
        if not package:
            package = next((p for p in all_regional_packages if p.get("packageCode") == package_code), None)
        if not package:
            package = next((p for p in all_global_packages if p.get("packageCode") == package_code), None)
        if not package:
            await query.message.reply_text("Package not found.")
            return

        duration = package.get("duration", 1)
        context.chat_data["pending_purchase"] = {
            "package_code": package_code,
            "order_price": package.get("price", 0),
            "retail_price": package.get("retailPrice", 0),
            "duration": duration
        }

        if duration == 1:
            await query.message.reply_text("🕓 This is a daily plan. How many days do you need?")
        else:
            await query.message.reply_text("📱 How many eSIMs would you like to purchase?")

    elif data.startswith("precancel_"):
        iccid = data.split("_", 1)[1]
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, cancel", callback_data=f"cancel_{iccid}"),
                InlineKeyboardButton("❌ No", callback_data="cancel_ignore")
            ]
        ])
        await query.message.reply_text(
            "⚠️ Are you sure you want to cancel this eSIM?\nThis action is irreversible and will refund the balance (if eligible).",
            reply_markup=keyboard
        )
        return

    elif data == "cancel_ignore":
        await query.message.reply_text("❎ Cancel request aborted.")
        return

    elif data.startswith("cancel_"):
        try:
            await query.answer()
            iccid = data.split("_", 1)[1]
            await query.message.reply_text("⏳ Cancelling eSIM...")

            session = SessionLocal()
            order = session.query(Order).filter(Order.iccid == iccid).first()

            if not order:
                await query.message.reply_text("❌ Order not found.")
                return

            logger.info(f"[Cancel] user={update.effective_user.id} → Requested cancel for ICCID {iccid}")

            # Проверим поддерживается ли cancel по статусам
            esim_data = buy_esim.query_esim_by_iccid(iccid)
            smdp = esim_data.get("smdpStatus")
            esim = esim_data.get("esimStatus")

            if smdp != "RELEASED" or esim != "GOT_RESOURCE":
                await query.message.reply_text(
                    "❌ This eSIM cannot be cancelled.\n"
                    "It may already be installed or activated on your device."
                )
                return

            # Cancel по esimTranNo
            esim_list = json.loads(order.esim_list or "[]")
            tran_no = esim_list[0].get("esimTranNo")

            result = buy_esim.cancel_esim(tran_no=tran_no)
            if result.get("success") is True:
                # Обновим БД
                updated_data = buy_esim.query_esim_by_iccid(iccid)
                buy_esim.update_order_from_api(session, iccid, updated_data)
                await query.message.reply_text(
                    "✅ eSIM successfully cancelled.\n"
                    "💸 A refund will be issued shortly."
                )
            else:
                err = result.get("errorMessage") or result.get("errorMsg") or "Unknown error"
                await query.message.reply_text(
                    "⚠️ The cancellation request is taking longer than expected.\n"
                    "Please try again in a few minutes or contact support if the issue persists."
                )
                logger.error(f"[Cancel API] Timeout or network error during cancel for ICCID {iccid}: {e}")
        except Exception as e:
            logger.exception("Cancel execution failed:")
            await query.message.reply_text(f"❌ Unexpected error:\n<code>{e}</code>", parse_mode="HTML")
        finally:
            session.close()

    elif data.startswith("topup_"):
        iccid = data.split("_", 1)[1]
        session = SessionLocal()
        order = session.query(Order).filter(Order.iccid == iccid).first()
        session.close()

        if not order:
            await query.message.reply_text("❌ eSIM not found in database.")
            logger.warning(f"[Top-Up] ICCID {iccid} not found in DB.")
            return

        try:
            esim_list = json.loads(order.esim_list)
            if not esim_list:
                await query.message.reply_text("❌ No eSIM profiles found.")
                return
            esim_tran_no = esim_list[0].get("esimTranNo")
        except Exception as e:
            await query.message.reply_text("❌ Failed to extract eSIM transaction number.")
            logger.exception("Failed to parse esim_list:")
            return

        if not esim_tran_no:
            await query.message.reply_text("❌ eSIM transaction number is missing.")
            logger.warning(f"[Top-Up] No esimTranNo found for ICCID {iccid}")
            return

        # Get top-up packages
        packages = await buy_esim.get_topup_packages(iccid)
        if not packages:
            await query.message.reply_text("❌ No available Top-Up packages.")
            return

        # ✅ Sort packages by retailPrice
        packages.sort(key=lambda p: int(p.get("retailPrice", 0)))

        # Render buttons
        buttons = []
        for pkg in packages:
            name = pkg.get("name", "")
            retail_price = int(pkg.get("retailPrice", 0)) / 10000
            pkg_code = pkg["packageCode"]
            raw_amount = int(pkg.get("price", 0))
            callback = f"topupdo|{esim_tran_no}|{pkg_code}|{raw_amount}"
            buttons.append([
                InlineKeyboardButton(f"💳 {name} — ${retail_price:.2f}", callback_data=callback)
            ])

        await query.message.reply_text(
            "Choose a top-up package:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("topupdo|"):
        try:
            await query.answer()
            _, tran_no, package_code, amount = data.split("|", 3)
            await query.message.reply_text("⏳ Please wait, processing your top-up...")

            logger.info(f"[Top-Up] user={update.effective_user.id} → Top-Up requested: tranNo={tran_no}, package={package_code}, amount={amount}")

            result = buy_esim.topup_esim(tran_no, package_code, int(amount))

            if result.get("success") is True:
                obj = result.get("obj", {})
                vol = int(obj.get("totalVolume", 0)) / 1024 / 1024
                dur = obj.get("totalDuration", "-")
                await query.message.reply_text(
                    f"✅ Top-up successful!\n📦 New data volume: {vol:.1f} MB\n⏳ Valid for: {dur} days"
                )

                # DB sync after top-up
                iccid = buy_esim.get_iccid_from_tranno(tran_no)
                if iccid:
                    session = SessionLocal()
                    try:
                        api_data = buy_esim.query_esim_by_iccid(iccid)
                        buy_esim.update_order_from_api(session, iccid, api_data)
                    except Exception as e:
                        logger.warning(f"[Top-Up] DB update failed after top-up: {e}")
                    finally:
                        session.close()
            else:
                err = result.get("errorMessage") or result.get("errorMsg") or "Unknown error"
                if "status doesn`t support" in err:
                    await query.message.reply_text(
                        "❌ Unable to top-up this eSIM: its current status does not allow it.\n\n"
                        "📌 This usually means the eSIM hasn't been activated on your device yet.\n"
                        "Top-up is only available after the eSIM has been installed and activated."
                    )
                else:
                    await query.message.reply_text(f"❌ Top-up failed: {err}")

        except Exception as e:
            logger.exception("Top-Up execution failed:")
            await query.message.reply_text(f"❌ Unexpected error:\n<code>{e}</code>", parse_mode="HTML")

    elif data.startswith("refresh_"):
        try:
            await query.answer()
            iccid = data.split("_", 1)[1]

            session = SessionLocal()
            order = session.query(Order).filter(Order.iccid == iccid).first()

            if not order:
                await query.message.reply_text("❌ Order not found.")
                return

            logger.info(f"[Refresh] user={update.effective_user.id} → Refresh usage for ICCID {iccid}")
            await query.message.reply_text("⏳ Syncing usage data...")
            try:
                esim_list = json.loads(order.esim_list or "[]")
            except Exception as e:
                logger.warning(f"[Refresh] Failed to parse esim_list: {e}")
                await query.message.reply_text("❌ Failed to parse eSIM profile info.")
                return

            if not esim_list or not esim_list[0].get("esimTranNo"):
                await query.message.reply_text("❌ eSIM profile info is missing.")
                return

            tran_no = esim_list[0]["esimTranNo"]

            # Проверка: только если eSIM активна
            api_data = buy_esim.query_esim_by_iccid(iccid)
            if api_data.get("esimStatus") != "IN_USE":
                await query.message.reply_text("⚠️ Usage data is only available for active eSIMs (IN_USE).")
                return

            # Обновляем usage
            usage_info = buy_esim.query_usage(tran_no)
            if usage_info:
                updated = buy_esim.update_usage_by_iccid(session, iccid, usage_info)
                if updated:
                    refreshed = buy_esim.query_esim_by_iccid(iccid)
                    msg = format_esim_info(refreshed, order)
                    await query.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)
                else:
                    await query.message.reply_text("⚠️ Usage data received but update failed.")
            else:
                await query.message.reply_text("❌ Failed to fetch usage data.")
        except Exception as e:
            logger.exception("Refresh usage failed:")
            await query.message.reply_text(f"❌ Unexpected error:\n<code>{e}</code>", parse_mode="HTML")
        finally:
            session.close()

def get_esim_status_label(smdp: str, esim: str) -> str:
    if smdp == "RELEASED" and esim == "GOT_RESOURCE":
        return "New"
    elif smdp == "ENABLED" and esim in {"IN_USE", "GOT_RESOURCE"}:
        return "Onboard"
    elif smdp == "ENABLED" and esim == "IN_USE":
        return "In Use"
    elif smdp in {"ENABLED", "DISABLED"} and esim == "USED_UP":
        return "Depleted"
    elif smdp == "DELETED" and esim in {"USED_UP", "IN_USE"}:
        return "Deleted"
    return f"{smdp} / {esim}"  # fallback

def format_esim_info(data: dict, db_entry: Optional[Order] = None) -> str:
    package_name = "-"
    if data.get("packageList") and isinstance(data["packageList"], list):
        package_name = data["packageList"][0].get("packageName", "-")

    usage = round(data.get("orderUsage", 0) / (1024 * 1024), 1)
    total = round(data.get("totalVolume", 1) / (1024 * 1024), 1)
    expired_raw = data.get("expiredTime", "N/A")
    expired = expired_raw[:10] if expired_raw != "N/A" else expired_raw
    esim = data.get("esimStatus", "N/A")
    smdp = data.get("smdpStatus", "N/A")
    status = get_esim_status_label(smdp, esim)
    qr = data.get("qrCodeUrl", "-").replace(".png", "")
    retail_price = round(db_entry.retail_price / 10000, 2) if db_entry and db_entry.retail_price else "-"

    # Order date
    order_date = "-"
    if data.get("packageList") and isinstance(data["packageList"], list):
        order_date_raw = data["packageList"][0].get("createTime")
        if order_date_raw:
            order_date = order_date_raw[:10]

    # Last sync time
    usage_sync = "-"
    if db_entry and db_entry.last_update_time:
        usage_sync = db_entry.last_update_time.strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"📱 <b>eSIM:</b> {package_name}\n"
        f"📦 <b>Data:</b> {total}MB | <b>Used:</b> {usage}MB\n"
        f"📅 <b>Order:</b> {order_date} | <b>Expires:</b> {expired}\n"
        f"📶 <b>Status:</b> {status}\n"
        f"💰 <b>Price:</b> ${retail_price}\n"
        f"🔄 <b>Usage Sync:</b> {usage_sync}\n"
        f"🔗 <b>QR:</b> <a href=\"{qr}\">Open Link</a>"
    )

def update_usage_by_iccid(db: Session, iccid: str, data: dict):
    order = db.query(Order).filter(Order.iccid == iccid).first()
    if not order:
        return False  # no match
    order.order_usage = data.get("orderUsage", order.order_usage)
    # ✅ Add this line:
    if "lastUpdateTime" in data:
        try:
            order.last_update_time = datetime.fromisoformat(data["lastUpdateTime"])
        except Exception:
            order.last_update_time = None
    db.commit()
    return True

async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def handle_message_wrapper(update: Update, context: CallbackContext) -> None:
    try:
        await handle_message(update, context)
    except Exception as e:
        logger.exception("Error in handle_message:")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_wrapper))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    application.run_polling()
