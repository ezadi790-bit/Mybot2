import logging
import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_USERNAME = "zoklik007"
ADMIN_CHAT_ID = None
REFERRAL_POINTS = 3
STARTING_POINTS = 6
IMAGE_COST = 3

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        points INTEGER DEFAULT 6,
        referred_by INTEGER,
        waiting_photo INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username, referred_by=None):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, points, referred_by) VALUES (?, ?, ?, ?)",
        (user_id, username, STARTING_POINTS, referred_by))
    conn.commit()
    conn.close()

def get_points(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_points(user_id, delta):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (delta, user_id))
    conn.commit()
    conn.close()

def set_waiting_photo(user_id, status):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET waiting_photo = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def is_waiting_photo(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT waiting_photo FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🖼 Create a new picture")],
        [KeyboardButton("💎 Buy the point")],
        [KeyboardButton("🔗 Forward the link and get free point")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_CHAT_ID
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    referred_by = None
    if context.args:
        try:
            referred_by = int(context.args[0])
            if referred_by == user_id:
                referred_by = None
        except:
            referred_by = None
    existing = get_user(user_id)
    is_new = existing is None
    add_user(user_id, username, referred_by)
    if username == ADMIN_USERNAME:
        ADMIN_CHAT_ID = user_id
    if is_new and referred_by:
        referrer = get_user(referred_by)
        if referrer:
            update_points(referred_by, REFERRAL_POINTS)
            try:
                await context.bot.send_message(chat_id=referred_by,
                    text=f"🎉 Someone joined using your link!\nYou received {REFERRAL_POINTS} points.")
            except:
                pass
    points = get_points(user_id)
    await update.message.reply_text(
        f"Welcome to this bot🌷\nYou have {points} point{'s' if points != 1 else ''}\n\nChoose your request👇",
        reply_markup=get_main_keyboard())

async def handle_create_picture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    points = get_points(user_id)
    if points < IMAGE_COST:
        await update.message.reply_text("⚠️ You have a few points, please increase them.", reply_markup=get_main_keyboard())
        return
    set_waiting_photo(user_id, 1)
    await update.message.reply_text("📸 Send a clear, high-quality photo of the person looking at the camera.", reply_markup=get_main_keyboard())

async def handle_buy_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔒 This request is temporarily unavailable.\nPlease try again later.", reply_markup=get_main_keyboard())

async def handle_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 Your personal referral link:\n\n`{link}`\n\nShare this link with others.\nFor each person who joins, you get {REFERRAL_POINTS} points! 🎁",
        parse_mode="Markdown", reply_markup=get_main_keyboard())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_CHAT_ID
    user_id = update.effective_user.id
    if not is_waiting_photo(user_id):
        await update.message.reply_text("Please use the menu below 👇", reply_markup=get_main_keyboard())
        return
    update_points(user_id, -IMAGE_COST)
    set_waiting_photo(user_id, 0)
    if ADMIN_CHAT_ID:
        try:
            user = update.effective_user
            await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID,
                text=f"📸 New photo from:\n👤 {user.first_name}\n🆔 @{user.username or 'no username'}\n🔢 ID: {user_id}")
        except Exception as e:
            logging.error(f"Error: {e}")
    points = get_points(user_id)
    await update.message.reply_text(
        f"✅ Please submit the media you want the image to be applied to.\nMedia must be under 10MB in size\n\n💎 Remaining points: {points}",
        reply_markup=get_main_keyboard())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🖼 Create a new picture":
        await handle_create_picture(update, context)
    elif text == "💎 Buy the point":
        await handle_buy_points(update, context)
    elif text == "🔗 Forward the link and get free point":
        await handle_referral_link(update, context)
    else:
        await update.message.reply_text("Please use the menu below 👇", reply_markup=get_main_keyboard())

def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
