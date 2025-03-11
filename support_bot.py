import sys
import logging
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Force UTF-8 encoding (Windows Fix)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Replace with your bot token and support group ID
BOT_TOKEN = "7784825740:AAGPb1Rp0yn3yOZzeVViSy5DblYJsR4Bu2c"
SUPPORT_GROUP_ID = -1002483073660  # Your support group chat ID

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def forward_to_support(update: Update, context: CallbackContext):
    """
    Forwards user messages to the support group.
    Skips processing if the message is already in the support group.
    """
    # If the message is in the support group, do nothing.
    if update.message.chat_id == SUPPORT_GROUP_ID:
        return

    user = update.message.from_user
    # Embed user's Telegram id in the message text.
    message_text = (
        f"📩 New support message from {user.first_name} (@{user.username}, id: {user.id}):\n\n"
        f"{update.message.text}"
    )
    
    # Forward the message to the support group
    await context.bot.send_message(chat_id=SUPPORT_GROUP_ID, text=message_text)
    # Reply to the user
    await update.message.reply_text("✅ Your message has been sent to support. A human agent will reply soon.")

async def forward_reply_to_user(update: Update, context: CallbackContext):
    """
    Forwards replies from the support group back to the user.
    Extracts the user ID from the original forwarded message using regex.
    """
    # Process only replies in the support group
    if update.message.reply_to_message and update.message.chat_id == SUPPORT_GROUP_ID:
        original_text = update.message.reply_to_message.text
        # Extract the user id from the text (assuming "id: <user_id>" format)
        match = re.search(r"id:\s*(\d+)", original_text)
        if match:
            user_id = int(match.group(1))
            reply_text = f"💬 Support Reply:\n\n{update.message.text}"
            await context.bot.send_message(chat_id=user_id, text=reply_text)
        else:
            logger.error("Could not extract user id from the forwarded message.")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register the reply handler first if needed,
    # but the key is to exclude replies in the generic handler.
    
    # Generic handler for user messages (ignores replies)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, forward_to_support))
    # Handler for replies in the support group
    app.add_handler(MessageHandler(filters.REPLY, forward_reply_to_user))
    
    print("🤖 Support Bot is running...")
    app.run_polling()
