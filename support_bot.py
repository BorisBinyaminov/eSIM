# Improved support_bot.py
import sys
import logging
import re
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
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



async def get_ai_response(prompt: str) -> str:
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
        response = client.chat.completions.create(model="gpt-3.5-turbo",
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
        response = client.chat.completions.create(model="gpt-3.5-turbo",
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
    # Ignore messages coming from the support group.
    if update.message.chat_id == SUPPORT_GROUP_ID:
        return

    # Initialize conversation log in context if it doesn't exist.
    if 'conversation' not in context.chat_data:
        context.chat_data['conversation'] = []

    user = update.message.from_user
    user_message = update.message.text.strip() if update.message.text else ""

    # Log text message if present.
    if user_message:
        context.chat_data['conversation'].append(f"User ({user.first_name}): {user_message}")

    # Handle photos (images/screenshots)
    if update.message.photo:
        # Get the highest resolution photo.
        photo = update.message.photo[-1]
        # Log that an image was sent without using the raw file_id.
        context.chat_data['conversation'].append(
            f"User ({user.first_name}): [Image sent – please check the forwarded image]"
        )
        # Forward the photo to the support group.
        await context.bot.send_photo(
            chat_id=SUPPORT_GROUP_ID,
            photo=photo.file_id,
            caption=f"Image from {user.first_name} (@{user.username})"
        )
        # Notify the user that the file will be reviewed by an agent.
        await update.message.reply_text("Your file has been received and will be reviewed by our support team.")

    if update.message.document:
        document = update.message.document
        file_name = document.file_name
        # Log that a file was sent and include its file name.
        context.chat_data['conversation'].append(
            f"User ({user.first_name}): [File sent: {file_name}, file_id: {document.file_id}]"
        )
        # Forward the document to the support group.
        await context.bot.send_document(
            chat_id=SUPPORT_GROUP_ID,
            document=document.file_id,
            caption=f"File from {user.first_name} (@{user.username}): {file_name}"
        )
        # Notify the user that the file will be reviewed by an agent.
        await update.message.reply_text("Your file has been received and will be reviewed by our support team.")

    # Use our AI-based escalation intent check (apply on text messages).
    escalation_triggered = await check_escalation_intent(user_message)
    if escalation_triggered:
        # Compile the conversation history.
        conversation_history = "\n\n".join(context.chat_data['conversation'])

        # Construct the file name and save the conversation log.
        LOG_FOLDER = "user_conv_logs"
        os.makedirs(LOG_FOLDER, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        username = user.username or user.first_name
        filename = os.path.join(LOG_FOLDER, f"{username}_{user.id}_{timestamp}.log")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(conversation_history)

        escalation_message = (
            f"📩 Escalation request from {user.first_name} (@{user.username}, id: {user.id}):\n\n"
            f"Conversation history saved to {filename}:\n{conversation_history}\n\n"
            f"Latest message: {user_message}"
        )
        await context.bot.send_message(chat_id=SUPPORT_GROUP_ID, text=escalation_message)
        await update.message.reply_text("Your conversation has been forwarded to our human support team. They will get back to you shortly.")
        # Optionally clear the conversation log after escalation.
        context.chat_data['conversation'] = []
    else:
        # Process the message normally using AI if there's text.
        if user_message:
            ai_response = await get_ai_response(user_message)
            context.chat_data['conversation'].append(f"Bot: {ai_response}")
            reply_text = f"💬 AI-generated Support Reply:\n\n{ai_response}"
            await update.message.reply_text(reply_text)

async def forward_reply_to_user(update: Update, context: CallbackContext):
    if update.message.reply_to_message and update.message.chat_id == SUPPORT_GROUP_ID:
        original_text = update.message.reply_to_message.text
        match = re.search(r"id:\s*(\d+)", original_text)

        if match:
            user_id = int(match.group(1))
            text = update.message.text

            if text.lower().startswith("/ai"):
                # Get the text after "/ai"
                prompt = text[3:].strip()
                # If no additional prompt is provided, extract the original user query
                if not prompt:
                    # The forwarded text format is: "📩 New support message from ...\n\n<user query>"
                    parts = original_text.split("\n\n", 1)
                    prompt = parts[1] if len(parts) > 1 else original_text
                ai_response = await get_ai_response(prompt)
                reply_text = f"💬 AI-generated Support Reply:\n\n{ai_response}"
            else:
                reply_text = f"💬 Support Reply:\n\n{text}"

            await context.bot.send_message(chat_id=user_id, text=reply_text)
        else:
            logger.error("Could not extract user id from the original message.")


if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.REPLY, forward_to_support))
    app.add_handler(MessageHandler(filters.REPLY, forward_reply_to_user))
    print("🤖 Support Bot is running...")
    app.run_polling()
