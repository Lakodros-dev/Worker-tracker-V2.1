"""Telegram Bot for Attendance System."""
import logging
from datetime import datetime
from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import config
from database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

USERS_FILE = "users.json"


def get_user(telegram_id: int):
    return db.find_one(USERS_FILE, "telegram_id", telegram_id)


def create_user(telegram_id: int, username: str, first_name: str, last_name: str):
    # Admin avtomatik active bo'ladi
    status = "active" if config.is_admin(telegram_id) else "pending"
    user = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "status": status,
        "created_at": datetime.now().isoformat()
    }
    db.append(USERS_FILE, user)
    return user


def update_user_status(telegram_id: int, status: str):
    return db.update(USERS_FILE, "telegram_id", telegram_id, {"status": status})


def get_users_by_status(status: str):
    return db.find_many(USERS_FILE, {"status": status})


def get_all_users():
    return db.read(USERS_FILE)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    db_user = get_user(user.id)
    
    if not db_user:
        db_user = create_user(user.id, user.username or "", user.first_name, user.last_name or "")
        await update.message.reply_text(
            f"Salom, {user.first_name}! 👋\n\n"
            "Siz tizimga muvaffaqiyatli ro'yxatdan o'tdingiz.\n"
            "Hisobingiz admin tomonidan tasdiqlanishini kuting.\n\n"
            "Status: ⏳ Kutilmoqda"
        )
        return
    
    if db_user["status"] == "pending":
        await update.message.reply_text(
            "⏳ Hisobingiz hali tasdiqlanmagan.\n"
            "Admin tasdiqlashini kuting."
        )
        return
    
    if db_user["status"] == "blocked":
        await update.message.reply_text("⛔ Sizning hisobingiz bloklangan.")
        return
    
    await show_main_menu(update, user.first_name)


async def show_main_menu(update: Update, name: str):
    """Show main menu with WebApp button."""
    keyboard = []
    
    if config.WEBAPP_URL:
        keyboard.append([KeyboardButton(text="📱 Ilovani ochish", web_app=WebAppInfo(url=config.WEBAPP_URL))])
    
    keyboard.append([KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)])
    keyboard.append([KeyboardButton(text="📊 Statistika"), KeyboardButton(text="ℹ️ Yordam")])
    
    await update.message.reply_text(
        f"Xush kelibsiz, {name}! ✅\n\n"
        "Ish vaqtida joylashuvingizni kuzatish uchun 8 soatlik jonli joylashuvni yuboring.\n\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "📋 *Davomat Tizimi - Yordam*\n\n"
        "*Asosiy buyruqlar:*\n"
        "/start - Tizimni boshlash\n"
        "/status - Bugungi holatni ko'rish\n"
        "/help - Yordam\n\n"
        "*Joylashuv kuzatuvi:*\n"
        "1. 📍 tugmasini bosing\n"
        "2. Jonli joylashuv tanlang\n"
        "3. 8 soat davomiylik tanlang\n\n"
        "*Admin:* /admin",
        parse_mode="Markdown"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id
    db_user = get_user(user_id)
    
    if not db_user:
        await update.message.reply_text("❌ Avval /start buyrug'ini yuboring.")
        return
    
    status_emoji = {"pending": "⏳", "active": "✅", "blocked": "⛔"}
    full_name = f"{db_user['first_name']} {db_user.get('last_name', '')}".strip()
    
    await update.message.reply_text(
        f"📊 *Holat*\n\n"
        f"👤 {full_name}\n"
        f"📌 Status: {status_emoji.get(db_user['status'], '❓')} {db_user['status']}",
        parse_mode="Markdown"
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command."""
    user_id = update.effective_user.id
    
    if not config.is_admin(user_id):
        await update.message.reply_text("⛔ Bu buyruq faqat adminlar uchun.")
        return
    
    pending = get_users_by_status("pending")
    active = get_users_by_status("active")
    
    keyboard = [
        [InlineKeyboardButton(f"👥 Kutilayotgan ({len(pending)})", callback_data="admin_pending")],
        [InlineKeyboardButton(f"✅ Faol ({len(active)})", callback_data="admin_active")],
    ]
    
    await update.message.reply_text(
        "🔐 *Admin Panel*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location updates."""
    user_id = update.effective_user.id
    location = update.message.location
    db_user = get_user(user_id)
    
    if not db_user or db_user["status"] != "active":
        await update.message.reply_text("⛔ Hisobingiz faol emas.")
        return
    
    if location.live_period:
        await update.message.reply_text(
            f"✅ Jonli joylashuv qabul qilindi!\n"
            f"Davomiyligi: {location.live_period // 3600} soat\n\n"
            f"📱 Mini App orqali to'liq ma'lumotlarni ko'ring."
        )
    else:
        await update.message.reply_text(
            "📍 Joylashuv qabul qilindi.\n\n"
            "💡 Uzluksiz kuzatuv uchun 8 soatlik jonli joylashuvni yuboring."
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not config.is_admin(user_id):
        await query.edit_message_text("⛔ Ruxsat yo'q")
        return
    
    data = query.data
    
    if data == "admin_pending":
        users = get_users_by_status("pending")
        if not users:
            await query.edit_message_text("✅ Kutilayotgan foydalanuvchilar yo'q")
            return
        
        keyboard = []
        for u in users[:10]:
            name = f"{u['first_name']} {u.get('last_name', '')}".strip()
            keyboard.append([
                InlineKeyboardButton(f"👤 {name}", callback_data=f"info_{u['telegram_id']}"),
                InlineKeyboardButton("✅", callback_data=f"approve_{u['telegram_id']}"),
                InlineKeyboardButton("⛔", callback_data=f"block_{u['telegram_id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")])
        
        await query.edit_message_text(
            "👥 *Kutilayotgan:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data == "admin_active":
        users = get_users_by_status("active")
        text = "✅ *Faol foydalanuvchilar:*\n\n"
        for u in users[:20]:
            name = f"{u['first_name']} {u.get('last_name', '')}".strip()
            text += f"• {name} (@{u.get('username') or 'N/A'})\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "admin_back":
        pending = get_users_by_status("pending")
        active = get_users_by_status("active")
        keyboard = [
            [InlineKeyboardButton(f"👥 Kutilayotgan ({len(pending)})", callback_data="admin_pending")],
            [InlineKeyboardButton(f"✅ Faol ({len(active)})", callback_data="admin_active")],
        ]
        await query.edit_message_text("🔐 *Admin Panel*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data.startswith("approve_"):
        target_id = int(data.split("_")[1])
        update_user_status(target_id, "active")
        await query.answer("✅ Tasdiqlandi")
        # Refresh pending list
        await handle_callback(update, context)
    
    elif data.startswith("block_"):
        target_id = int(data.split("_")[1])
        update_user_status(target_id, "blocked")
        await query.answer("⛔ Bloklandi")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    text = update.message.text
    
    if text == "📊 Statistika":
        await status_command(update, context)
    elif text == "ℹ️ Yordam":
        await help_command(update, context)


def main():
    """Run the bot."""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is required!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
