import sys
import logging
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# ✅ Force UTF-8 encoding (Windows Fix)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Replace with your bot token
BOT_TOKEN = "7784825740:AAGPb1Rp0yn3yOZzeVViSy5DblYJsR4Bu2c"
SUPPORT_GROUP_ID = 5102625060  # Replace with your group chat ID

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def forward_to_support(update: Update, context: CallbackContext):
    """Forwards user messages to the support group"""
    user = update.message.from_user
    message_text = f"📩 New support message from {user.first_name} (@{user.username}):\n\n{update.message.text}"
    
    # Forward the message to the support group
    await context.bot.send_message(chat_id=SUPPORT_GROUP_ID, text=message_text)

    # Reply to user
    await update.message.reply_text("✅ Your message has been sent to support. A human agent will reply soon.")

async def forward_reply_to_user(update: Update, context: CallbackContext):
    """Forwards replies from support group back to the user"""
    if update.message.reply_to_message and update.message.chat_id == SUPPORT_GROUP_ID:
        # Extract the original user's username
        user_tag = update.message.reply_to_message.text.split("(@")[1].split(")")[0] if "(@" in update.message.reply_to_message.text else None
        
        if user_tag:
            # Send response to user
            await context.bot.send_message(chat_id=f"@{user_tag}", text=f"💬 Support Reply:\n\n{update.message.text}")

# Initialize the bot
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_support))
    app.add_handler(MessageHandler(filters.REPLY, forward_reply_to_user))
    
    print("🤖 Support Bot is running...")
    app.run_polling()
