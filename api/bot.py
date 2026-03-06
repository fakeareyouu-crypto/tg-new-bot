import os
import telebot
from flask import Flask, request, render_template_string
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

if not BOT_TOKEN or not ADMIN_ID:
    raise Exception("Missing BOT_TOKEN or ADMIN_ID")

ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

LOG_FILE = "/tmp/logs.txt"


def log_message(user, message):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = user.username if user.username else "NoUsername"

    log = f"[{time}] {username} ({user.id}): {message}\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log)


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Welcome! Send a message to contact the admin.")


@bot.message_handler(func=lambda m: True)
def contact_admin(message):

    user = message.from_user
    text = message.text

    log_message(user, text)

    admin_msg = f"""
📩 New Message

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

    html = f"""
    <html>
    <head>
    <title>Bot Logs</title>
    <style>
    body{{background:#0f172a;color:#00ff9c;font-family:monospace;padding:30px}}
    .box{{background:#020617;padding:20px;border-radius:10px;height:80vh;overflow:auto}}
    </style>
    </head>
    <body>
    <h1>Telegram Bot Logs</h1>
    <div class="box"><pre>{logs}</pre></div>
    </body>
    </html>
    """

    return html


@app.route("/webhook", methods=["POST"])
def webhook():

    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])

    return "OK"


@app.route("/setwebhook")
def set_webhook():

    url = os.environ.get("VERCEL_URL")

    if not url:
        return "VERCEL_URL not set"

    webhook_url = f"https://{url}/webhook"

    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

    return f"Webhook set to {webhook_url}"
