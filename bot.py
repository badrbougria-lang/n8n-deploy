import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
CPA_LINK = os.environ.get("CPA_LINK", "https://passwordomain.com/1881602")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_user(user_id: str):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"coins": 0, "completed_offer": False, "referrals": 0, "referred_by": None}
        save_db(db)
    return db[user_id]

def update_user(user_id: str, data: dict):
    db = load_db()
    if user_id not in db:
        db[user_id] = data
    else:
        db[user_id].update(data)
    save_db(db)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        user_data = get_user(user_id)
        if user_data["referred_by"] is None and referrer_id != user_id:
            update_user(user_id, {"referred_by": referrer_id})
    get_user(user_id)
    keyboard = [
        [InlineKeyboardButton("🎁 احصل على Coins مجاناً", callback_data="get_coins")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")],
    ]
    await update.message.reply_text(
        f"🔥 مرحباً {user.first_name}!\n\n🎮 بوت FF Rewards!\n\n✅ أكمل مهمة واحصل على:\n💎 100 Coins مجاناً\n👥 + 50 Coins لكل صديق\n\nاختر من القائمة 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    await query.answer()

    if query.data == "get_coins":
        if user_data["completed_offer"]:
            await query.edit_message_text(f"✅ أكملت المهمة!\n💰 رصيدك: {user_data['coins']} Coins")
        else:
            keyboard = [
                [InlineKeyboardButton("✅ أكملت المهمة!", callback_data="verify_offer")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
            ]
            await query.edit_message_text(
                f"🎯 خطوة واحدة!\n\n1️⃣ افتح الرابط\n2️⃣ أكمل المهمة\n3️⃣ ارجع واضغط ✅\n\n🔗 {CPA_LINK}\n\n💎 ستحصل على 100 Coins!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "verify_offer":
        if not user_data["completed_offer"]:
            new_coins = user_data["coins"] + 100
            update_user(user_id, {"completed_offer": True, "coins": new_coins})
            if user_data["referred_by"]:
                referrer_id = user_data["referred_by"]
                referrer_data = get_user(referrer_id)
                update_user(referrer_id, {"coins": referrer_data["coins"] + 50, "referrals": referrer_data["referrals"] + 1})
                try:
                    await context.bot.send_message(chat_id=int(referrer_id), text=f"🎉 صديقك أكمل المهمة!\n💰 ربحت 50 Coins!\n💎 رصيدك: {referrer_data['coins'] + 50} Coins")
                except:
                    pass
            await query.edit_message_text(f"🎉 تهانينا!\n✅ 100 Coins تمت إضافتها!\n💰 رصيدك: {new_coins} Coins\n\n👥 ادعو أصدقاء واربح أكثر!\n/ref")

    elif query.data == "balance":
        await query.edit_message_text(f"💰 رصيدك:\n\n💎 Coins: {user_data['coins']}\n👥 أصدقاء: {user_data['referrals']}")

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(f"👥 رابط الدعوة:\n\n🔗 {ref_link}\n\n💰 50 Coins لكل صديق!\n👥 دعوت: {user_data['referrals']} أصدقاء")

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🎁 احصل على Coins مجاناً", callback_data="get_coins")],
            [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
            [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")],
        ]
        await query.edit_message_text("🔥 القائمة الرئيسية\n\nاختر 👇", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    total = len(db)
    completed = sum(1 for u in db.values() if u.get("completed_offer"))
    await update.message.reply_text(f"📊 إحصائيات:\n👥 المستخدمين: {total}\n✅ أكملوا: {completed}\n❌ لم يكملوا: {total - completed}")

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 البوت شغال!")
    app.run_polling()

if __name__ == "__main__":
    main()
