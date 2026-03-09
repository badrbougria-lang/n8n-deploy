import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# الإعدادات
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
CPA_LINK = os.environ.get("CPA_LINK", "https://passwordomain.com/1881602")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1002341506")) # الرقم ديالك من الصور
CHANNEL_USERNAME = "@ffrewards_ma" # اسم القناة ديالك
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

# دالة التحقق من الاشتراك في القناة
async def is_subscribed(context, user_id):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False
    except Exception:
        return True # في حالة وقوع خطأ تقني، نخليه يمر

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    get_user(user_id)

    # التحقق من الإحالة
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        user_data = get_user(user_id)
        if user_data["referred_by"] is None and referrer_id != user_id:
            update_user(user_id, {"referred_by": referrer_id})

    # رسالة ترحيب مع التحقق من القناة
    subscribed = await is_subscribed(context, user.id)
    
    if not subscribed:
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ تم الاشتراك، ابدأ الآن", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            f"⚠️ **عفواً {user.first_name}!**\n\nيجب عليك الاشتراك في قناة البوت الرسمية أولاً لتتمكن من جمع الجوائز.\n\nاشترك ثم اضغط على زر التأكيد 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = [
        [InlineKeyboardButton("🎁 ابدأ واربح Coins", callback_data="get_coins")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")],
    ]
    await update.message.reply_text(f"🔥 مرحباً {user.first_name}!\nأكمل المهمة واحصل على مكافأتك 👇", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    await query.answer()

    if query.data == "check_sub":
        if await is_subscribed(context, query.from_user.id):
            await query.edit_message_text("✅ شكراً لثقتك! يمكنك الآن البدء:")
            # عرض القائمة الرئيسية بعد التأكد
            keyboard = [[InlineKeyboardButton("🎁 ابدأ واربح Coins", callback_data="get_coins")]]
            await query.message.reply_text("اختر المهمة 👇", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer("❌ مازال ما اشتركتيش في القناة!", show_alert=True)

    elif query.data == "get_coins":
        keyboard = [[InlineKeyboardButton("🔗 افتح الرابط وأكمل المهمة", url=CPA_LINK)]]
        await query.edit_message_text("🎯 أكمل المهمة في الرابط، ثم انتظر 30 ثانية ليظهر زر التأكيد 👇", reply_markup=InlineKeyboardMarkup(keyboard))
        await asyncio.sleep(WAIT_SECONDS)
        keyboard_after = [[InlineKeyboardButton("✅ خذ Coins ديالك!", callback_data="verify_offer")]]
        try: await query.edit_message_text("⏰ انتهى الوقت! اضغط للتأكيد 👇", reply_markup=InlineKeyboardMarkup(keyboard_after))
        except: pass

    elif query.data == "verify_offer":
        update_user(user_id, {"waiting_for_id": True, "completed_offer": True, "coins": user_data["coins"] + 100})
        await query.edit_message_text("🎉 تهانينا! دابا صيفط ID ديال Free Fire ديالك هنا:")

    elif query.data == "balance":
        await query.edit_message_text(f"💰 رصيدك: {user_data['coins']} Coins")

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(f"👥 رابطك: {ref_link}\n💰 50 Coins عن كل إحالة!")

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
                text=f"🚀 **طلب شحن جديد!**\n\n👤 المستخدم: {update.effective_user.first_name}\n🆔 Telegram ID: `{user_id}`\n🎮 **Free Fire ID: `{ff_id}`**"
            )
        except: pass

        await update.message.reply_text(f"✅ تم استلام الـ ID بنجاح! سيتم الشحن قريباً 🔥")
    else:
        await update.message.reply_text("استخدم القائمة للتحكم في البوت.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 البوت شغال مع نظام القناة!")
    app.run_polling()

if __name__ == "__main__":
    main()
