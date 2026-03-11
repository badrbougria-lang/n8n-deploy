import json
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات الأساسية (المستخرجة من صورك) ---
BOT_TOKEN = "7864448553:AAF-U4Y8v5-qR5u4U9Vv5_T8" # تأكدي أن هذا التوكن لا يزال فعالاً في BotFather
ADMIN_ID = 1002341506  # الـ ID الخاص بكِ لاستقبال الطلبات
CPA_LINK = "https://passwordomain.com/1881602" # رابط الربح المحدث
DB_FILE = "users.json"

# إعداد السجلات لمراقبة الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_user(uid):
    db = load_db()
    uid = str(uid)
    if uid not in db:
        db[uid] = {"coins": 0, "referrals": 0, "waiting": False}
        save_db(db)
    return db[uid]

def update_user(uid, data):
    db = load_db()
    uid = str(uid)
    if uid in db:
        db[uid].update(data)
        save_db(db)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    get_user(uid)

    # نظام الإحالة
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        db = load_db()
        if referrer_id in db and uid not in db:
            db[referrer_id]["coins"] += 50
            save_db(db)

    keyboard = [
        [InlineKeyboardButton("💎 شحن الجواهر", callback_data="coins")],
        [InlineKeyboardButton("💰 رصيدي الحالي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="ref")]
    ]

    await update.message.reply_text(
        f"🔥 أهلاً بك يا {user.first_name}!\n\nاجمع النقاط الآن واشحن جواهر فري فاير مجاناً!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = str(query.from_user.id)
    data = get_user(uid)
    await query.answer()

    if query.data == "coins":
        keyboard = [[InlineKeyboardButton("🔗 اضغط هنا لإكمال المهمة", url=CPA_LINK)]]
        await query.edit_message_text(
            "⚠️ للتحقق من هويتك، يرجى إكمال المهمة في الرابط أدناه، ثم أرسل الـ ID الخاص بك هنا للحصول على 100 نقطة.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        update_user(uid, {"waiting": True})

    elif query.data == "balance":
        await query.edit_message_text(f"💰 رصيدك الحالي: {data['coins']} نقطة.")

    elif query.data == "ref":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=ref_{uid}"
        await query.edit_message_text(f"👥 شارك الرابط واحصل على 50 نقطة لكل صديق:\n\n{link}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = get_user(uid)

    if data.get("waiting"):
        ffid = update.message.text
        update_user(uid, {"waiting": False, "coins": data["coins"] + 100})
        
        # إرسال إشعار للأدمن
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚀 طلب شحن جديد\nالمستخدم: {uid}\nالـ ID المطلوب: {ffid}"
        )
        await update.message.reply_text("✅ تم استلام الـ ID! سيتم التحقق والشحن خلال ساعات.")

def main():
    # استخدام التوكن المدمج مباشرة لحل مشكلة الـ InvalidToken
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
