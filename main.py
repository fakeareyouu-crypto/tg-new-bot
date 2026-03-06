"""Telegram contact bot with a Flask dashboard for live message logs."""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template
import telebot
from telebot.apihelper import ApiTelegramException

# -----------------------------------------------------------------------------
# Configuration and constants
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "logs.txt"

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()
PORT = int(os.getenv("PORT", "5000"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Set it in your .env file.")

if not ADMIN_ID_RAW:
    raise ValueError("ADMIN_ID is missing. Set it in your .env file.")

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError as exc:
    raise ValueError("ADMIN_ID must be a valid integer Telegram user ID.") from exc

# Configure Python logger for stdout and troubleshooting.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Telegram bot and Flask app.
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)


# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------
def ensure_log_file() -> None:
    """Create logs file if it does not already exist."""
    LOG_FILE.touch(exist_ok=True)


def format_log_entry(message: telebot.types.Message) -> str:
    """Build one line of log text for a Telegram message."""
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    username = message.from_user.username or message.from_user.first_name or "unknown_user"
    user_id = message.from_user.id
    text = (message.text or "").strip()
    return f"[{date_time}] {username} ({user_id}): {text}"


def append_log(entry: str) -> None:
    """Append one formatted line to logs.txt."""
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(entry + "\n")


def read_logs() -> str:
    """Read the entire log file and return as plain text."""
    if not LOG_FILE.exists():
        return "No logs yet."
    return LOG_FILE.read_text(encoding="utf-8").strip() or "No logs yet."


def safe_send_message(chat_id: int, text: str) -> None:
    """Send Telegram messages with basic API error handling."""
    try:
        bot.send_message(chat_id, text)
    except ApiTelegramException:
        logger.exception("Failed to send message to chat_id=%s", chat_id)


# -----------------------------------------------------------------------------
# Bot command handlers
# -----------------------------------------------------------------------------
@bot.message_handler(commands=["start"])
def handle_start(message: telebot.types.Message) -> None:
    """Handle /start command."""
    welcome_text = (
        "👋 <b>Welcome to the Contact Bot</b>\n\n"
        "Use this bot to send a message directly to the admin.\n"
        "Commands:\n"
        "• /contact - Send your message to the admin\n"
        "• /help - Show help instructions"
    )
    safe_send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=["help"])
def handle_help(message: telebot.types.Message) -> None:
    """Handle /help command."""
    help_text = (
        "ℹ️ <b>Help</b>\n\n"
        "This bot forwards your message to the admin.\n"
        "How to use:\n"
        "1) Send /contact\n"
        "2) Type your message in your next text message\n\n"
        "Your message will be logged and forwarded."
    )
    safe_send_message(message.chat.id, help_text)


@bot.message_handler(commands=["contact"])
def handle_contact(message: telebot.types.Message) -> None:
    """Handle /contact command."""
    prompt = "✉️ Please send the message you want to deliver to the admin."
    safe_send_message(message.chat.id, prompt)


@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_user_message(message: telebot.types.Message) -> None:
    """Handle all text messages: log, forward to admin, and acknowledge sender."""
    if message.text and message.text.startswith("/"):
        # Ignore unknown slash commands so they are not logged as contact messages.
        return

    entry = format_log_entry(message)
    append_log(entry)
    logger.info("Logged message: %s", entry)

    username = message.from_user.username or message.from_user.first_name or "unknown_user"
    forward_text = (
        "📩 <b>New contact message received</b>\n\n"
        f"From: {username} ({message.from_user.id})\n"
        f"Message: {message.text}"
    )

    safe_send_message(ADMIN_ID, forward_text)
    safe_send_message(
        message.chat.id,
        "Your message has been sent to the admin. You will be contacted if necessary.",
    )


# -----------------------------------------------------------------------------
# Flask routes
# -----------------------------------------------------------------------------
@app.route("/")
def index() -> str:
    """Render dashboard page."""
    return render_template("index.html")


@app.route("/api/logs")
def api_logs():
    """Return current logs as JSON for auto-refresh in dashboard."""
    return jsonify({"logs": read_logs()})


# -----------------------------------------------------------------------------
# Runtime
# -----------------------------------------------------------------------------
def run_bot() -> None:
    """Start Telegram bot polling loop."""
    logger.info("Starting Telegram bot polling...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=20)


def run_web() -> None:
    """Start Flask web server."""
    logger.info("Starting Flask web server on port %s...", PORT)
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


def main() -> None:
    """Create required resources and run bot + web server simultaneously."""
    ensure_log_file()

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    run_web()


if __name__ == "__main__":
    main()
