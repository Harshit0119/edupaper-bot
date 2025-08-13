import os
import mysql.connector
from dotenv import load_dotenv
from flask import Flask
import threading
import logging 

# ✅ Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Connect to MySQL
db = mysql.connector.connect(
    host=DB_HOST,
    port=int(DB_PORT or 3306),
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    connection_timeout=10
)
cursor = db.cursor()

# Store user state
user_data = {}

# Bot handlers (same as before)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start triggered by {user.username} ({user.id})")
    keyboard = [
        [InlineKeyboardButton("Class 10", callback_data='class10')],
        [InlineKeyboardButton("Class 12", callback_data='class12')],
        [InlineKeyboardButton("B.Tech", callback_data='btech')]
    ]
    await update.message.reply_text(
        "📚 Welcome to EduPaper Archive!\nChoose your course:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def course_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    course = query.data
    user_data[query.from_user.id] = {'course': course}

    if course == 'class10':
        subjects = ['maths', 'science', 'english', 'social']
        keyboard = [[InlineKeyboardButton(sub.capitalize(), callback_data='static_link')] for sub in subjects]
        await query.edit_message_text(
            f"📘 You selected *Class 10*.\nChoose a subject:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif course == 'class12':
        streams = ['PCM', 'PCB', 'Commerce']
        keyboard = [[InlineKeyboardButton(stream, callback_data=f"stream_{stream.lower()}")] for stream in streams]
        await query.edit_message_text(
            "📚 You selected *Class 12*.\nPlease choose your stream:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        branches = ['cse', 'me', 'ec', 'eee', 'ce', 'aiml']
        keyboard = [[InlineKeyboardButton(br.upper(), callback_data=f"branch_{br}")] for br in branches]
        await query.edit_message_text(
            "🧑‍🎓 You selected *B.Tech*.\nChoose your branch:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

import json
def markup_changed(old_markup, new_markup):
    if not old_markup or not new_markup:
        return True
    return json.dumps(old_markup.to_dict(), sort_keys=True) != json.dumps(new_markup.to_dict(), sort_keys=True)

async def stream_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stream = query.data.replace("stream_", "")
    user_data[query.from_user.id]['stream'] = stream

    if stream == 'pcm':
        subjects = ['maths', 'physics', 'chemistry', 'english']
    elif stream == 'pcb':
        subjects = ['biology', 'physics', 'chemistry', 'english']
    elif stream == 'commerce':
        subjects = ['accountancy', 'business studies', 'economics', 'english']
    else:
        subjects = ['english']

    new_text = f"🧪 Stream selected: *{stream.upper()}*\nChoose a subject:"
    new_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(sub.capitalize(), callback_data='static_link')] for sub in subjects]
    )

    if query.message.text != new_text or markup_changed(query.message.reply_markup, new_markup):
        await query.edit_message_text(
            text=new_text,
            reply_markup=new_markup,
            parse_mode="Markdown"
        )

async def btech_branch_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    branch = query.data.replace("branch_", "")
    user_data[query.from_user.id]['branch'] = branch

    semesters = [f'sem{i}' for i in range(1, 9)]
    keyboard = [[InlineKeyboardButton(sem.upper(), callback_data='static_link')] for sem in semesters]
    await query.message.reply_text(
        f"🧠 Branch selected: *{branch.upper()}*\nNow choose your semester:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def send_static_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "📄 *Your Study Material is Ready!*\n"
        "[Click here to access previous year papers](http://edupaper-archive.netlify.app)\n\n"
        "Made with ❤️ by *Harshit*",
        parse_mode="Markdown"
    )

    await query.message.reply_text(
        "📢 *We value your FEEDBACK!*\n\n"
        "💬 *We'd love to hear from you!*\n"
        "Tell us what you think — your feedback helps us improve EduPaper Archive.\n\n"
        "📝 *What can you share?*\n"
        "• What you liked or didn’t like\n"
        "• Any missing papers or broken links\n"
        "• Ideas to make this platform better\n\n"
        "👉 *JUST TYPE YOUR MESSAGE below and HIT send!*\n\n"
        "_Made with ❤️ by Harshit_",
        parse_mode="Markdown"
    )

    user_data[query.from_user.id]['awaiting_feedback'] = True

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.from_user.id
    if user_data.get(telegram_id, {}).get('awaiting_feedback'):
        try:
            feedback_text = update.message.text
            name = update.message.from_user.full_name

            cursor.execute(
                "INSERT INTO feedback (telegram_id, username, feedback) VALUES (%s, %s, %s)",
                (telegram_id, name, feedback_text)
            )
            db.commit()

            await update.message.reply_text("🙏 Thank you for your feedback! It helps us improve.")
            user_data[telegram_id]['awaiting_feedback'] = False
        except Exception as e:
         logger.error(f"Error saving feedback: {e}")
         await update.message.reply_text("⚠️ Sorry, something went wrong while saving your feedback.")

# Flask app to satisfy Render's Web Service requirement
app = Flask(__name__)

@app.route('/health')
def health():
    return "EduPaper Bot is running!", 200

# Run bot in background thread
import asyncio

def run_bot():
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    asyncio.set_event_loop(asyncio.new_event_loop())

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(course_selected, pattern='^(class10|class12|btech)$'))
    app.add_handler(CallbackQueryHandler(stream_selected, pattern='^stream_'))
    app.add_handler(CallbackQueryHandler(btech_branch_selected, pattern='^branch_'))
    app.add_handler(CallbackQueryHandler(send_static_link, pattern='^static_link$'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback))

    logger.info("✅ Bot is running...")
    app.run_polling()

# Start both Flask and bot
if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=10000)
