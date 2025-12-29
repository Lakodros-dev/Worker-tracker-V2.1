"""Telegram Bot for Attendance System."""
import logging
import random
import string
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import config
from database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

USERS_FILE = "users.json"
USERS_PER_PAGE = 10

# Global bot instance for sending messages
bot_app = None


async def get_user(telegram_id: int):
    return await db.find_one(USERS_FILE, "telegram_id", telegram_id)


async def create_user(telegram_id: int, username: str, first_name: str, last_name: str):
    """Create new user with pending status (admin is auto-active)."""
    status = "active" if config.is_admin(telegram_id) else "pending"
    password = None
    if status == "active":
        password = ''.join(random.choices(string.digits, k=5))
    
    user = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "status": status,
        "password": password,
        "auth_type": "telegram",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    success = await db.append(USERS_FILE, user)
    return user if success else None


def generate_password():
    """Generate 5-digit password."""
    return ''.join(random.choices(string.digits, k=5))


async def update_user(telegram_id: int, updates: dict):
    """Update user data."""
    updates["updated_at"] = datetime.now().isoformat()
    return await db.update(USERS_FILE, "telegram_id", telegram_id, updates)


async def get_users_by_status(status: str):
    return await db.find_many(USERS_FILE, {"status": status})


async def get_all_users():
    return await db.read(USERS_FILE)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    db_user = await get_user(user.id)
    
    # Update existing user info if changed
    if db_user:
        needs_update = (
            db_user.get("username") != (user.username or "") or
            db_user.get("first_name") != user.first_name or
            db_user.get("last_name") != (user.last_name or "")
        )
        if needs_update:
            await update_user(user.id, {
                "username": user.username or "",
                "first_name": user.first_name,
                "last_name": user.last_name or ""
            })
    
    if not db_user:
        db_user = await create_user(user.id, user.username or "", user.first_name, user.last_name or "")
        if not db_user:
            await update.message.reply_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
            return
        
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
    """Show main menu."""
    keyboard = []
    
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
    db_user = await get_user(user_id)
    
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
    
    await show_admin_panel(update.message)


async def show_admin_panel(message, edit: bool = False):
    """Show admin panel with user counts."""
    pending = await get_users_by_status("pending")
    active = await get_users_by_status("active")
    blocked = await get_users_by_status("blocked")
    
    keyboard = [
        [InlineKeyboardButton(f"👥 Kutilayotgan ({len(pending)})", callback_data="admin_pending_0")],
        [InlineKeyboardButton(f"✅ Faol ({len(active)})", callback_data="admin_active_0")],
        [InlineKeyboardButton(f"⛔ Bloklangan ({len(blocked)})", callback_data="admin_blocked_0")],
    ]
    
    text = "🔐 *Admin Panel*"
    
    if edit:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location updates."""
    user_id = update.effective_user.id
    location = update.message.location
    db_user = await get_user(user_id)
    
    if not db_user:
        await update.message.reply_text("❌ Avval /start buyrug'ini yuboring.")
        return
    
    if db_user["status"] != "active":
        await update.message.reply_text("⛔ Hisobingiz faol emas.")
        return
    
    if location.live_period:
        hours = location.live_period // 3600
        minutes = (location.live_period % 3600) // 60
        duration = f"{hours} soat" if hours else f"{minutes} daqiqa"
        
        await update.message.reply_text(
            f"✅ Jonli joylashuv qabul qilindi!\n"
            f"📍 Koordinatalar: {location.latitude:.6f}, {location.longitude:.6f}\n"
            f"⏱ Davomiyligi: {duration}\n\n"
            f"📱 Mini App orqali to'liq ma'lumotlarni ko'ring."
        )
    else:
        await update.message.reply_text(
            f"📍 Joylashuv qabul qilindi.\n"
            f"Koordinatalar: {location.latitude:.6f}, {location.longitude:.6f}\n\n"
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
    
    # Parse callback data
    if data.startswith("admin_pending_"):
        page = int(data.split("_")[2])
        await show_pending_users(query, page)
    
    elif data.startswith("admin_active_"):
        page = int(data.split("_")[2])
        await show_users_list(query, "active", page)
    
    elif data.startswith("admin_blocked_"):
        page = int(data.split("_")[2])
        await show_users_list(query, "blocked", page)
    
    elif data == "admin_back":
        await show_admin_panel(query.message, edit=True)
    
    elif data.startswith("approve_"):
        target_id = int(data.split("_")[1])
        target_user = await get_user(target_id)
        
        # Parol generatsiya qilish
        password = generate_password()
        await update_user(target_id, {"status": "active", "password": password})
        
        # Foydalanuvchiga parol yuborish
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎉 *Hisobingiz tasdiqlandi!*\n\n"
                    "Endi siz tizimdan foydalanishingiz mumkin.\n\n"
                    "🔐 *Browser orqali kirish uchun:*\n"
                    f"👤 Username: `{target_user.get('username', 'N/A')}`\n"
                    f"🔑 Parol: `{password}`\n\n"
                    "⚠️ Bu parolni xavfsiz joyda saqlang!"
                ),
                parse_mode="Markdown"
            )
            await query.answer("✅ Tasdiqlandi va parol yuborildi", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to send password to user {target_id}: {e}")
            await query.answer(f"✅ Tasdiqlandi. Parol: {password}", show_alert=True)
        
        await show_pending_users(query, 0)
    
    elif data.startswith("block_"):
        target_id = int(data.split("_")[1])
        await update_user(target_id, {"status": "blocked"})
        await query.answer("⛔ Bloklandi", show_alert=True)
        await show_pending_users(query, 0)
    
    elif data.startswith("unblock_"):
        target_id = int(data.split("_")[1])
        target_user = await get_user(target_id)
        
        # Yangi parol generatsiya qilish
        password = generate_password()
        await update_user(target_id, {"status": "active", "password": password})
        
        # Foydalanuvchiga xabar yuborish
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🔓 *Hisobingiz blokdan chiqarildi!*\n\n"
                    "🔐 *Yangi kirish ma'lumotlari:*\n"
                    f"👤 Username: `{target_user.get('username', 'N/A')}`\n"
                    f"🔑 Yangi parol: `{password}`\n\n"
                    "⚠️ Bu parolni xavfsiz joyda saqlang!"
                ),
                parse_mode="Markdown"
            )
            await query.answer("✅ Blokdan chiqarildi va yangi parol yuborildi", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to send password to user {target_id}: {e}")
            await query.answer(f"✅ Blokdan chiqarildi. Yangi parol: {password}", show_alert=True)
        
        await show_users_list(query, "blocked", 0)
    
    elif data.startswith("info_"):
        target_id = int(data.split("_")[1])
        await show_user_info(query, target_id)


async def show_pending_users(query, page: int):
    """Show pending users with pagination."""
    users = await get_users_by_status("pending")
    
    if not users:
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")]]
        await query.edit_message_text(
            "✅ Kutilayotgan foydalanuvchilar yo'q",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    page = max(0, min(page, total_pages - 1))
    start = page * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]
    
    keyboard = []
    for u in page_users:
        name = f"{u['first_name']} {u.get('last_name', '')}".strip()
        keyboard.append([
            InlineKeyboardButton(f"👤 {name[:20]}", callback_data=f"info_{u['telegram_id']}"),
            InlineKeyboardButton("✅", callback_data=f"approve_{u['telegram_id']}"),
            InlineKeyboardButton("⛔", callback_data=f"block_{u['telegram_id']}")
        ])
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_pending_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_pending_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")])
    
    await query.edit_message_text(
        f"👥 *Kutilayotgan foydalanuvchilar:* ({len(users)} ta)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_users_list(query, status: str, page: int):
    """Show users list with pagination."""
    users = await get_users_by_status(status)
    status_titles = {"active": "✅ Faol", "blocked": "⛔ Bloklangan"}
    
    if not users:
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")]]
        await query.edit_message_text(
            f"{status_titles.get(status, status)} foydalanuvchilar yo'q",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    page = max(0, min(page, total_pages - 1))
    start = page * USERS_PER_PAGE
    end = start + USERS_PER_PAGE
    page_users = users[start:end]
    
    text = f"{status_titles.get(status, status)} *foydalanuvchilar:* ({len(users)} ta)\n\n"
    
    keyboard = []
    for u in page_users:
        name = f"{u['first_name']} {u.get('last_name', '')}".strip()
        username = f"@{u.get('username')}" if u.get('username') else "N/A"
        text += f"• {name} ({username})\n"
        
        if status == "blocked":
            keyboard.append([
                InlineKeyboardButton(f"👤 {name[:15]}", callback_data=f"info_{u['telegram_id']}"),
                InlineKeyboardButton("🔓 Ochish", callback_data=f"unblock_{u['telegram_id']}")
            ])
    
    # Pagination
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_{status}_{page-1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_{status}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_user_info(query, telegram_id: int):
    """Show detailed user info."""
    user = await get_user(telegram_id)
    
    if not user:
        await query.answer("Foydalanuvchi topilmadi", show_alert=True)
        return
    
    status_emoji = {"pending": "⏳", "active": "✅", "blocked": "⛔"}
    name = f"{user['first_name']} {user.get('last_name', '')}".strip()
    username = f"@{user.get('username')}" if user.get('username') else "N/A"
    password = user.get('password', 'Yo\'q')
    
    text = (
        f"👤 *Foydalanuvchi ma'lumotlari*\n\n"
        f"📛 Ism: {name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: `{telegram_id}`\n"
        f"📌 Status: {status_emoji.get(user['status'], '❓')} {user['status']}\n"
        f"🔑 Parol: `{password}`\n"
        f"📅 Ro'yxatdan o'tgan: {user.get('created_at', 'N/A')[:10]}"
    )
    
    keyboard = []
    if user['status'] == "pending":
        keyboard.append([
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{telegram_id}"),
            InlineKeyboardButton("⛔ Bloklash", callback_data=f"block_{telegram_id}")
        ])
    elif user['status'] == "active":
        keyboard.append([InlineKeyboardButton("⛔ Bloklash", callback_data=f"block_{telegram_id}")])
    elif user['status'] == "blocked":
        keyboard.append([InlineKeyboardButton("🔓 Blokdan chiqarish", callback_data=f"unblock_{telegram_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


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
        logger.error("BOT_TOKEN is required! Set it in .env file")
        return
    
    if not config.ADMIN_IDS:
        logger.warning("No ADMIN_IDS configured. Admin features will be unavailable.")
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("admin", admin_command))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
