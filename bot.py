import logging
import os
import sqlite3
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 8234019630
ADMIN_USERNAME = "zoklik007"
CHANNEL_ID = -1003917459204
REFERRAL_POINTS = 3
STARTING_POINTS = 6
IMAGE_COST = 3
FAKE_MEMBER_COUNT = "12,450"

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        points INTEGER DEFAULT 6,
        referred_by INTEGER,
        waiting_photo INTEGER DEFAULT 0,
        waiting_media INTEGER DEFAULT 0,
        join_time TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS media_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        media_type TEXT,
        time TEXT)""")
    for col in ["first_name", "join_time", "waiting_media"]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        except:
            pass
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username, first_name, referred_by=None):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, points, referred_by, join_time) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, first_name, STARTING_POINTS, referred_by, now))
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

def set_waiting_media(user_id, status):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET waiting_media = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def is_waiting_media(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT waiting_media FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def log_media(user_id, username, media_type):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO media_log (user_id, username, media_type, time) VALUES (?, ?, ?, ?)",
        (user_id, username, media_type, now))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, points, join_time FROM users ORDER BY join_time DESC")
    users = c.fetchall()
    conn.close()
    return users

def get_all_user_ids():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids

def get_media_log():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, media_type, time FROM media_log ORDER BY time DESC LIMIT 20")
    logs = c.fetchall()
    conn.close()
    return logs

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🖼 Create a new picture")],
        [KeyboardButton("💎 Buy the point")],
        [KeyboardButton("🔗 Forward the link and get free point")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_start_keyboard():
    keyboard = [[KeyboardButton("/start")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton("👥 Users"), KeyboardButton("📁 Media Log")],
        [KeyboardButton("✉️ Send Message"), KeyboardButton("💰 Add Points")],
        [KeyboardButton("📢 Broadcast"), KeyboardButton("🏠 Main Menu")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

ADMIN_STATE = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""

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
    add_user(user_id, username, first_name, referred_by)

    if is_new and referred_by:
        referrer = get_user(referred_by)
        if referrer:
            update_points(referred_by, REFERRAL_POINTS)
            try:
                await context.bot.send_message(
                    chat_id=referred_by,
                    text=f"🎉 Someone joined using your referral link!\nYou received {REFERRAL_POINTS} points! 🎁")
            except:
                pass

    set_waiting_photo(user_id, 0)
    set_waiting_media(user_id, 0)
    ADMIN_STATE.pop(user_id, None)
    points = get_points(user_id)

    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "👑 Admin Panel\nWelcome back!\n\nChoose an option:",
            reply_markup=get_admin_keyboard())
    else:
        await update.message.reply_text(
            f"Welcome to this bot🌷\n👥 Members: {FAKE_MEMBER_COUNT}\n"
            f"You have {points} point{'s' if points != 1 else ''}\n\nChoose your request👇",
            reply_markup=get_main_keyboard())

async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return False

    text = update.message.text

    if ADMIN_STATE.get(user_id) == "broadcast":
        ADMIN_STATE.pop(user_id, None)
        all_ids = get_all_user_ids()
        success = 0
        fail = 0
        for uid in all_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                success += 1
                await asyncio.sleep(0.05)
            except:
                fail += 1
        await update.message.reply_text(
            f"📢 Broadcast done!\n✅ Sent: {success}\n❌ Failed: {fail}",
            reply_markup=get_admin_keyboard())
        return True

    if text == "👥 Users":
        users = get_all_users()
        msg = f"👥 Total Users: {len(users)}\n\n"
        for u in users[:20]:
            uid, uname, fname, pts, jtime = u
            msg += f"👤 {fname} | @{uname or 'none'}\n🆔 {uid} | 💎 {pts}pts | 🕐 {jtime}\n\n"
        await update.message.reply_text(msg, reply_markup=get_admin_keyboard())
        return True

    elif text == "📁 Media Log":
        logs = get_media_log()
        msg = "📁 Recent Media:\n\n"
        for log in logs:
            uid, uname, mtype, time = log
            msg += f"🆔 {uid} | @{uname or 'none'}\n📎 {mtype} | 🕐 {time}\n\n"
        await update.message.reply_text(msg or "No media yet.", reply_markup=get_admin_keyboard())
        return True

    elif text == "✉️ Send Message":
        await update.message.reply_text(
            "Send message in this format:\n\n`/send USER_ID your message here`",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard())
        return True

    elif text == "💰 Add Points":
        await update.message.reply_text(
            "Add points in this format:\n\n`/addpoints USER_ID amount`",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard())
        return True

    elif text == "📢 Broadcast":
        ADMIN_STATE[user_id] = "broadcast"
        await update.message.reply_text(
            "✍️ Write your broadcast message and send it:",
            reply_markup=get_admin_keyboard())
        return True

    elif text == "🏠 Main Menu":
        await update.message.reply_text("Main menu:", reply_markup=get_main_keyboard())
        return True

    return False

async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /send USER_ID message")
        return
    try:
        target_id = int(context.args[0])
        message = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=target_id, text=f"📨 Message from admin:\n\n{message}")
        await update.message.reply_text("✅ Message sent!", reply_markup=get_admin_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}", reply_markup=get_admin_keyboard())

async def cmd_addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpoints USER_ID amount")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        update_points(target_id, amount)
        pts = get_points(target_id)
        await update.message.reply_text(f"✅ Added {amount} points.\nNew balance: {pts}", reply_markup=get_admin_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}", reply_markup=get_admin_keyboard())

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
    bot_info = await context.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 Your personal referral link:\n\n`{link}`\n\nShare this link with others.\nFor each person who joins, you get {REFERRAL_POINTS} points! 🎁",
        parse_mode="Markdown", reply_markup=get_main_keyboard())

async def send_rejection_message(context, chat_id):
    await asyncio.sleep(60)
    await context.bot.send_message(
        chat_id=chat_id,
        text="❌ The photo you sent could not be processed. Please try again.\n\nWays your photo could be rejected:\n1_ Poor quality\n2_ Face angled\n3_ Excessive image shake",
        reply_markup=get_start_keyboard())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user

    if is_waiting_photo(user_id):
        update_points(user_id, -IMAGE_COST)
        set_waiting_photo(user_id, 0)
        set_waiting_media(user_id, 1)
        log_media(user_id, user.username or "", "face_photo")
        try:
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.send_message(chat_id=ADMIN_ID,
                text=f"📸 Face photo from:\n👤 {user.first_name}\n🆔 @{user.username or 'none'}\n🔢 ID: {user_id}")
        except Exception as e:
            logging.error(f"Error: {e}")
        points = get_points(user_id)
        await update.message.reply_text(
            f"✅ Please submit the media you want the image to be applied to.\nMedia must be under 10MB in size\n\n💎 Remaining points: {points}",
            reply_markup=get_main_keyboard())

    elif is_waiting_media(user_id):
        set_waiting_media(user_id, 0)
        log_media(user_id, user.username or "", "media_photo")
        try:
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.send_message(chat_id=ADMIN_ID,
                text=f"🎬 Media from:\n👤 {user.first_name}\n🆔 @{user.username or 'none'}\n🔢 ID: {user_id}")
        except Exception as e:
            logging.error(f"Error: {e}")
        await update.message.reply_text("⏳ Processing photo...")
        asyncio.create_task(send_rejection_message(context, update.message.chat_id))
    else:
        await update.message.reply_text("Please use the menu below 👇", reply_markup=get_main_keyboard())

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    if is_waiting_media(user_id):
        set_waiting_media(user_id, 0)
        log_media(user_id, user.username or "", "video")
        try:
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.send_message(chat_id=ADMIN_ID,
                text=f"🎬 Video from:\n👤 {user.first_name}\n🆔 @{user.username or 'none'}\n🔢 ID: {user_id}")
        except Exception as e:
            logging.error(f"Error: {e}")
        await update.message.reply_text("⏳ Processing photo...")
        asyncio.create_task(send_rejection_message(context, update.message.chat_id))
    else:
        await update.message.reply_text("Please use the menu below 👇", reply_markup=get_main_keyboard())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        handled = await handle_admin(update, context)
        if handled:
            return

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
    add_user(ADMIN_ID, "zoklik007", "Admin")
    update_points(ADMIN_ID, 100)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", cmd_send))
    app.add_handler(CommandHandler("addpoints", cmd_addpoints))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
