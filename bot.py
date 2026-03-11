import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات (تأكدي من صحة التوكن الجديد) ---
BOT_TOKEN = "ضع_التوكن_الجديد_هنا_من_BotFather"
ADMIN_ID = 1002341506
CPA_LINK = "https://passwordomain.com/1881602"
# ------------------------------------------

WAIT_SECONDS = 30
DB_FILE = "users.json"

# دالة لتحميل البيانات مع معالجة الأخطاء
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                content = f.read()
                return json.loads(content) if content else {}
        except:
            return {}
    return {}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except:
        pass

def get_user(user_id: str):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"coins": 0, "completed_offer": False, "referrals": 0, "referred_by": None, "waiting_for_id": False, "timer_active": False}
        save_db(db)
    return db[user_id]

def update_user(user_id: str, data: dict):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"coins": 0, "completed_offer": False, "referrals": 0, "referred_by": None, "waiting_for_id": False, "timer_active": False}
    db[user_id].update(data)
    save_db(db)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🎁 احصل على نقاطك مجاناً", callback_data="get_coins")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="referral")],
    ]
    await update.message.reply_text(f"🔥 مرحباً بك {user.first_name}!\n\nاختر من القائمة أدناه 👇", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    await query.answer()

    if query.data == "get_coins":
        if user_data.get("timer_active"):
            await query.answer("⏳ انتظر حتى ينتهي العد التنازلي!", show_alert=True)
            return
        
        keyboard = [[InlineKeyboardButton("🔗 افتح الرابط وأكمل المهمة", url=CPA_LINK)]]
        await query.edit_message_text("🎯 أكمل المهمة في الرابط وانتظر 30 ثانية لتستلم جائزتك...", reply_markup=InlineKeyboardMarkup(keyboard))
        
        update_user(user_id, {"timer_active": True})
        await asyncio.sleep(WAIT_SECONDS)
        update_user(user_id, {"timer_active": False})
        
        keyboard_after = [[InlineKeyboardButton("✅ استلم نقاطك الآن!", callback_data="verify_offer")]]
        await query.edit_message_text("⏰ انتهى الوقت! إذا أكملت المهمة اضغط أدناه:", reply_markup=InlineKeyboardMarkup(keyboard_after))

    elif query.data == "verify_offer":
        update_user(user_id, {"coins": user_data["coins"] + 100, "waiting_for_id": True})
        await query.edit_message_text("🎉 أحسنت! أرسل الآن الـ ID الخاص بك لشحن الجواهر:")

    elif query.data == "balance":
        await query.edit_message_text(f"💰 رصيدك الحالي: {user_data['coins']} نقطة.")

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        await query.edit_message_text(f"👥 رابط الدعوة الخاص بك:\nhttps://t.me/{bot_username}?start=ref_{user_id}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    if user_data.get("waiting_for_id"):
        ff_id = update.message.text
        update_user(user_id, {"waiting_for_id": False})
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🚀 طلب شحن جديد:\nID: {ff_id}\nUser: {user_id}")
        await update.message.reply_text("✅ تم استلام الـ ID! سيتم الشحن قريباً.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
