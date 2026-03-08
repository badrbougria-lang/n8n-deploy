import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# الإعدادات
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
CPA_LINK = os.environ.get("CPA_LINK", "https://passwordomain.com/1881602")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
WAIT_SECONDS = 30
DB_FILE = "users.json"

# وظائف قاعدة البيانات
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_user(user_id: str):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"coins": 0, "completed_offer": False, "referrals": 0, "referred_by": None, "waiting_for_id": False}
        save_db(db)
    return db[user_id]

def update_user(user_id: str, data: dict):
    db = load_db()
    if user_id in db:
        db[user_id].update(data)
        save_db(db)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    user_data = get_user(user_id)

    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        if user_data["referred_by"] is None and referrer_id != user_id:
            update_user(user_id, {"referred_by": referrer_id})

    keyboard = [
        [InlineKeyboardButton("🎁 احصل على Coins مجاناً", callback_data="get_coins")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")],
    ]
    await update.message.reply_text(f"🔥 مرحباً {user.first_name}!\n\n🎮 بوت FF Rewards!\n\nأكمل المهمة واحصل على مكافأتك 👇", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    await query.answer()

    if query.data == "get_coins":
        if user_data["completed_offer"]:
            await query.edit_message_text("✅ أكملت المهمة من قبل! صيفط الـ ID ديالك إلا مزال ما شحنتي.")
        else:
            keyboard = [[InlineKeyboardButton("🔗 افتح الرابط وأكمل المهمة", url=CPA_LINK)]]
            await query.edit_message_text("🎯 أكمل المهمة في الرابط، ثم انتظر 30 ثانية ليظهر زر التأكيد 👇", reply_markup=InlineKeyboardMarkup(keyboard))
            await asyncio.sleep(WAIT_SECONDS)
            keyboard_after = [[InlineKeyboardButton("✅ خذ Coins ديالك!", callback_data="verify_offer")]]
            try: await query.edit_message_text("⏰ انتهى الوقت! اضغط للتأكيد 👇", reply_markup=InlineKeyboardMarkup(keyboard_after))
            except: pass

    elif query.data == "verify_offer":
        update_user(user_id, {"waiting_for_id": True, "completed_offer": True, "coins": user_data["coins"] + 100})
        
        if user_data["referred_by"]:
            referrer_id = str(user_data["referred_by"])
            r_data = get_user(referrer_id)
            update_user(referrer_id, {"coins": r_data["coins"] + 50, "referrals": r_data["referrals"] + 1})
            try: await context.bot.send_message(chat_id=int(referrer_id), text="🎉 صديقك أكمل المهمة! ربحت 50 Coins.")
            except: pass

        await query.edit_message_text("🎉 تهانينا! تمت إضافة 100 Coins.\n\n👇 **دابا صيفط ID ديال Free Fire ديالك هنا باش نشحن ليك:**")

    elif query.data == "balance":
        await query.edit_message_text(f"💰 رصيدك: {user_data['coins']} Coins\n👥 الإحالات: {user_data['referrals']}")

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(f"👥 نظام الإحالة:\n\n🔗 رابطك: {ref_link}\n\n💰 شارك الرابط مع صحابك واربح 50 Coins على كل واحد!")

# الدالة المحدثة لاستقبال الـ ID وتحفيز المستخدم على الإحالة
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)

    if user_data.get("waiting_for_id"):
        ff_id = update.message.text
        update_user(user_id, {"waiting_for_id": False})
        
        # إشعار للآدمين
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚀 **طلب شحن جديد!**\n\n👤 المستخدم: {update.effective_user.first_name}\n🆔 Telegram ID: `{user_id}`\n🎮 **Free Fire ID: `{ff_id}`**\n💰 الرصيد: {user_data['coins']}"
            )
        except: pass

        # استخراج رابط الإحالة
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        # الرسالة النهائية للمستخدم
        await update.message.reply_text(
            f"✅ تم استلام الـ ID بنجاح: `{ff_id}`\n\n"
            f"سيتم مراجعة الطلب وشحن حسابك في أقرب وقت! 🔥\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💎 **بغيتي تربح مجوهرات أكثر؟**\n"
            f"صيفط هاد الرابط لصحابك، وعلى كل واحد كمل مهمة غاتاخد **50 Coins** إضافية!\n\n"
            f"🔗 رابط الدعوة ديالك:\n`{ref_link}`"
        )
    else:
        await update.message.reply_text("استخدم الأزرار في القائمة للتحكم في البوت.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 البوت شغال!")
    app.run_polling()

if __name__ == "__main__":
    main()
