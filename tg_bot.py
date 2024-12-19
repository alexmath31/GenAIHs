from telegram import Bot, Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
import logging
import os

load_dotenv()

BOT_TOKEN = os.getenv('bot_token')

ADMINS = [123456789]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)


def send_date_message(user_id_1, user_id_2):
    """
    Sends a simple message to two users via the Telegram bot.
    """
    try:
        message = "Here is your Date!"
        
        bot.send_message(chat_id=user_id_1, text=message)
        bot.send_message(chat_id=user_id_2, text=message)
        
        print(f"Message sent to User {user_id_1} and User {user_id_2}.")
    except Exception as e:
        print(f"Error: {e}")


def start(update: Update, context: CallbackContext):
    """Send a welcome message to the user."""
    update.message.reply_text(
        "👋 Welcome to the PairBot!\n\n"
        "Use /help to see available commands.\n"
        "Admins can use the admin panel commands."
    )


def help_command(update: Update, context: CallbackContext):
    """Display help information."""
    update.message.reply_text(
        "📚 *Available Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/pair <user1_id> <user2_id> - Pair two users (Admin only)\n",
        parse_mode=ParseMode.MARKDOWN
    )


def pair(update: Update, context: CallbackContext):
    """Pair two users and send them an attractive message."""
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    args = context.args
    if len(args) != 2:
        update.message.reply_text("⚠️ Please provide exactly two user IDs. Example: /pair 123456789 987654321")
        return

    user_id_1, user_id_2 = args

    try:
        send_date_message(user_id_1, user_id_2)
        update.message.reply_text(f"✅ Successfully paired {user_id_1} and {user_id_2}.")
    except Exception as e:
        update.message.reply_text(f"❌ An error occurred: {e}")

def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("pair", pair))

    logger.info("Bot is running...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()