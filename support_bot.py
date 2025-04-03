# Improved support_bot.py
import sys
import logging
import re
import os
from openai import OpenAI
import asyncio
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext, CommandHandler
from faq_entries import FAQ_ENTRIES
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
import os
import datetime
import logging

# Force UTF-8 encoding (Windows Fix)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

FAQ_TEXT = "\n\n".join(
    f"Q: {faq['question']}\nA: {faq['answer']}" for faq in FAQ_ENTRIES
)

# Replace with your bot token and support group ID
BOT_TOKEN = "7784825740:AAGPb1Rp0yn3yOZzeVViSy5DblYJsR4Bu2c"
SUPPORT_GROUP_ID = -1002483073660

# Set your OpenAI API key from environment variable

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
global_human_sessions = {}



async def get_ai_response(prompt: str, context_history: list = None):
    """
    Improved AI response handling:
    - Properly differentiates between greetings and real issues.
    - Provides step-by-step troubleshooting for detailed queries.
    - Avoids repeated requests for clarification.
    """
    prompt_clean = prompt.strip().lower()

    # Define common generic greetings
    generic_greetings = {"hi", "hello", "hey", "hi there", "hello there", "greetings"}

    # Check if the user message is just a greeting
    if prompt_clean in generic_greetings or len(prompt_clean) <= 5:
        system_message = (
            "You are an eSIM support assistant. "
            "If a user sends a greeting without describing an issue, ask them for specific details. "
            "Encourage them to mention whether they are facing connectivity issues, activation errors, or network settings problems."
        )
        user_prompt = "User only sent a greeting. Ask them to describe their eSIM issue."
    else:
        system_message = (
            "You are an eSIM support expert for the eSIM Unlimited product. "
            "Below is a list of frequently asked questions (FAQ) you should be familiar with:\n\n"
            f"{FAQ_TEXT}\n\n"
            "Use this information to help troubleshoot user issues. "
            "If the user provides a detailed issue, generate a step-by-step troubleshooting guide that includes verifying activation, checking APN settings, ensuring automatic network selection, enabling data roaming, restarting the device, and updating carrier settings. "
            "If none of these steps resolve the issue, instruct the user to provide additional details for internal escalation rather than asking them to contact an external provider."
        )
        user_prompt = prompt  # Keep the original user input for detailed queries

    try:
        response = client.chat.completions.create(
        timeout=8,model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=400)
        ai_reply = response.choices[0].message.content.strip()
        logging.info(f"AI Response generated successfully: {ai_reply}")
        return ai_reply
    except Exception as e:
        logging.error(f"Error generating AI response: {e}")
        return "I'm sorry, I couldn't generate a response at the moment."

async def check_escalation_intent(message: str) -> bool:
    # Prepare the prompt for detecting escalation intent.
    prompt = (
        "Does the following message indicate that the user is requesting to speak with a human support agent? "
        "Answer only 'yes' or 'no'.\n\n"
        f"Message: {message}"
    )
    try:
        response = client.chat.completions.create(
        timeout=8,model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that identifies if a user message is an escalation request."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,  # deterministic output
        max_tokens=10)
        answer = response.choices[0].message.content.strip().lower()
        return answer.startswith("yes")
    except Exception as e:
        # Fallback to a conservative approach if the call fails.
        return False

async def forward_to_support(update: Update, context: CallbackContext):
    if update.message.chat_id == SUPPORT_GROUP_ID:
        return

    user = update.message.from_user
    user_id = update.message.chat_id
    msg = update.message.text or "[non-text]"

    if 'conversation' not in context.chat_data:
        context.chat_data['conversation'] = []

    if global_human_sessions.get(user_id):
        if update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(chat_id=SUPPORT_GROUP_ID, photo=photo.file_id,
                                         caption=f"📷 Photo from {user.first_name} (@{user.username}, id: {user.id})")
        elif update.message.document:
            doc = update.message.document
            await context.bot.send_document(chat_id=SUPPORT_GROUP_ID, document=doc.file_id,
                                            caption=f"📎 File from {user.first_name} (@{user.username}, id: {user.id}): {doc.file_name}")
        else:
            await context.bot.send_message(
                chat_id=SUPPORT_GROUP_ID,
                text=f"📨 Message from {user.first_name} (@{user.username}, id: {user.id}):\n{msg}"
            )
        return

    context.chat_data['conversation'].append(f"User ({user.first_name}): {msg}")

    if update.message.photo:
        context.chat_data['conversation'].append(f"User ({user.first_name}): [Photo sent]")
        await context.bot.send_photo(chat_id=SUPPORT_GROUP_ID, photo=update.message.photo[-1].file_id,
                                     caption=f"📷 Photo from {user.first_name} (@{user.username}, id: {user.id})")
        await update.message.reply_text("✅ Your image has been sent to support.")
        return

    if update.message.document:
        context.chat_data['conversation'].append(f"User ({user.first_name}): [File sent: {update.message.document.file_name}]")
        await context.bot.send_document(chat_id=SUPPORT_GROUP_ID, document=update.message.document.file_id,
                                        caption=f"📎 File from {user.first_name} (@{user.username}, id: {user.id}): {update.message.document.file_name}")
        await update.message.reply_text("✅ Your file has been sent to support.")
        return

    if any(p in msg.lower() for p in ["human", "agent", "real person", "talk to support"]):
        log = "\n\n".join(context.chat_data['conversation'])
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_conv_logs/{user.username or user.id}_{timestamp}.log"
        os.makedirs("user_conv_logs", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(log)

        await context.bot.send_message(
            chat_id=SUPPORT_GROUP_ID,
            text=f"📩 Escalation from {user.first_name} (@{user.username}, id: {user.id})\nConversation saved to {filename}"
        )
        await update.message.reply_text("A human agent has been notified.")
        global_human_sessions[user_id] = True
        asyncio.create_task(auto_disable_human_mode(user_id, context))
        return

    reply = await get_ai_response(msg, context.chat_data['conversation'])
    context.chat_data['conversation'].append(f"Bot: {reply}")
    try:
        await update.message.reply_text(f"💬 {reply}")
    except Exception as e:
        logger.error(f"Reply send error: {e}")

async def forward_reply_to_user(update: Update, context: CallbackContext):
    if update.message.reply_to_message and update.message.chat_id == SUPPORT_GROUP_ID:
        reply_text = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
        match = re.search(r"id:\s*(\d+)", reply_text)
        if not match:
            return

        user_id = int(match.group(1))
        text = update.message.text or ""

        if text.strip().lower().startswith("/done"):
            global_human_sessions[user_id] = False
            try:
                await context.bot.send_message(chat_id=user_id, text="✅ Session ended. You can now chat with AI again.")
                await update.message.reply_text(f"🟢 Session ended for user id: {user_id} — human mode off.")
            except Exception as e:
                await update.message.reply_text(f"⚠️ Could not notify user {user_id}.")
                logger.warning(f"Failed to notify user {user_id}: {e}")
            return

        await context.bot.send_message(chat_id=user_id, text=text)

async def stop_human_mode(update: Update, context: CallbackContext):
    reply = update.message.reply_to_message
    user_id = None

    # Case 1: reply to a message with id:
    if reply:
        reply_text = reply.text or reply.caption or ""
        match = re.search(r"id:\s*(\d+)", reply_text)
        if match:
            user_id = int(match.group(1))

    # Case 2: /done <user_id> as argument
    elif context.args and context.args[0].isdigit():
        user_id = int(context.args[0])

    # If we have the user_id, proceed
    if user_id:
        global_human_sessions[user_id] = False
        try:
            await context.bot.send_message(chat_id=user_id, text="✅ Session ended. You can now chat with AI again.")
            await update.message.reply_text(f"🟢 Session ended for user id: {user_id} — human mode off.")
        except Exception as e:
            logger.warning(f"Could not notify user {user_id}: {e}")
            await update.message.reply_text(f"⚠️ Human mode disabled, but could not send message to user {user_id}.")
    else:
        await update.message.reply_text("⚠️ Please reply to a user message or provide a user ID like /done 123456789")


async def auto_disable_human_mode(user_id: int, context: CallbackContext):
    await asyncio.sleep(60)
    if global_human_sessions.get(user_id):
        global_human_sessions[user_id] = False
        await context.bot.send_message(chat_id=user_id, text="ℹ️ Session expired. AI assistant is back.")
        await context.bot.send_message(chat_id=SUPPORT_GROUP_ID, text=f"⏱️ Session timeout for user {user_id}")

def create_bot_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.REPLY, forward_to_support))
    app.add_handler(MessageHandler(filters.REPLY, forward_reply_to_user))
    return app

