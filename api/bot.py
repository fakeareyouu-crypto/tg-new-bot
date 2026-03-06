import os
import telebot
from flask import Flask, request, render_template
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__, template_folder="../templates")

LOG_FILE = "logs.txt"


def log_message(user, message):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log = f"[{time}] {user.username} ({user.id}): {message}\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log)


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Welcome!\n\nThis is a contact bot.\nSend your message and it will reach the admin."
    )


@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(
        message,
        "/start - Start bot\n"
        "/help - Show help\n\n"
        "Just send any message to contact the admin."
    )


@bot.message_handler(func=lambda m: True)
def contact_admin(message):

    user = message.from_user
    text = message.text

    log_message(user, text)

    admin_msg = f"""
📩 New Contact Message

User: @{user.username}
ID: {user.id}

Message:
{text}
"""

    bot.send_message(ADMIN_ID, admin_msg)

    bot.reply_to(message, "✅ Your message has been sent to the admin.")


@app.route("/")
def index():

    logs = ""

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.read()

    return render_template("index.html", logs=logs)


@app.route("/webhook", methods=["POST"])
def webhook():

    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])

    return "OK", 200


@app.route("/setwebhook")
def set_webhook():

    url = os.environ.get("VERCEL_URL")

    webhook_url = f"https://{url}/webhook"

    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

    return f"Webhook set to {webhook_url}"
