import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
CPA_LINK = os.environ.get("CPA_LINK", "https://passwordomain.com/1881602")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
WAIT_SECONDS = 30

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
        db[user_id] = {
            "coins": 0,
            "completed_offer": False,
            "referrals": 0,
            "referred_by": None,
            "timer_started": False
        }
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

    # إشعار الأدمين
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 مستخدم جديد!\nالاسم: {user.first_name}\nID: {user_id}"
        )
    except:
        pass

    keyboard = [
        [InlineKeyboardButton("🎁 احصل على Coins مجاناً", callback_data="get_coins")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")],
    ]
    await update.message.reply_text(
        f"🔥 مرحباً {user.first_name}!\n\n"
        f"🎮 بوت FF Rewards!\n\n"
        f"✅ أكمل مهمة واحدة واحصل على:\n"
        f"💎 100 Coins مجاناً\n"
        f"👥 50 Coins لكل صديق تدعوه\n\n"
        f"اختر من القائمة 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    await query.answer()

    if query.data == "get_coins":
        if user_data["completed_offer"]:
            await query.edit_message_text(
                f"✅ أكملت المهمة من قبل!\n"
                f"💰 رصيدك: {user_data['coins']} Coins\n\n"
                f"👥 ادعو أصدقاء لتربح أكثر!\n/ref"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔗 افتح الرابط وأكمل المهمة", url=CPA_LINK)],
                [InlineKeyboardButton("⏳ انتظر 30 ثانية بعد الإكمال...", callback_data="wait")]
            ]
            await query.edit_message_text(
                f"🎯 خطوة واحدة فقط!\n\n"
                f"1️⃣ اضغط على الرابط أسفله\n"
                f"2️⃣ أكمل المهمة البسيطة\n"
                f"3️⃣ استنى 30 ثانية\n"
                f"4️⃣ سيظهر زر المطالبة بـ Coins تلقائياً!\n\n"
                f"💎 ستحصل على 100 Coins!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            update_user(user_id, {"timer_started": True})

            # Timer 30 ثانية
            await asyncio.sleep(WAIT_SECONDS)

            if not get_user(user_id)["completed_offer"]:
                keyboard_after = [
                    [InlineKeyboardButton("✅ خذ Coins ديالك!", callback_data="verify_offer")],
                ]
                try:
                    await query.edit_message_text(
                        f"⏰ انتهى الوقت!\n\n"
                        f"إذا أكملت المهمة، اضغط أسفله 👇\n"
                        f"💎 100 Coins في انتظارك!",
                        reply_markup=InlineKeyboardMarkup(keyboard_after)
                    )
                except:
                    pass

    elif query.data == "wait":
        await query.answer("⏳ استنى! سيظهر الزر بعد 30 ثانية من فتح الرابط!", show_alert=True)

    elif query.data == "verify_offer":
        if not user_data["completed_offer"]:
            new_coins = user_data["coins"] + 100
            update_user(user_id, {
                "completed_offer": True,
                "coins": new_coins,
                "timer_started": False
            })

            # Referral bonus
            if user_data["referred_by"]:
                referrer_id = user_data["referred_by"]
                referrer_data = get_user(referrer_id)
                update_user(referrer_id, {
                    "coins": referrer_data["coins"] + 50,
                    "referrals": referrer_data["referrals"] + 1
                })
                try:
                    await context.bot.send_message(
                        chat_id=int(referrer_id),
                        text=f"🎉 صديقك أكمل المهمة!\n💰 ربحت 50 Coins!\n💎 رصيدك: {referrer_data['coins'] + 50} Coins"
                    )
                except:
                    pass

            # إشعار الأدمين
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"✅ مستخدم أكمل المهمة!\nID: {user_id}\n💰 Coins: {new_coins}"
                )
            except:
                pass

            await query.edit_message_text(
                f"🎉 تهانينا!\n\n"
                f"✅ تم إضافة 100 Coins!\n"
                f"💰 رصيدك الآن: {new_coins} Coins\n\n"
                f"👥 ادعو أصدقاء واربح 50 Coins لكل واحد!"
            )

    elif query.data == "balance":
        await query.edit_message_text(
            f"💰 رصيدك:\n\n"
            f"💎 Coins: {user_data['coins']}\n"
            f"👥 أصدقاء دعوتهم: {user_data['referrals']}\n"
            f"💵 قيمتها: {user_data['referrals'] * 50} Coins من الدعوات"
        )

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(
            f"👥 رابط الدعوة ديالك:\n\n"
            f"🔗 {ref_link}\n\n"
            f"💰 50 Coins لكل صديق يكمل المهمة!\n"
            f"👥 دعوت: {user_data['referrals']} أصدقاء\n"
            f"💎 ربحت: {user_data['referrals'] * 50} Coins"
        )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    total = len(db)
    completed = sum(1 for u in db.values() if u.get("completed_offer"))
    await update.message.reply_text(
        f"📊 إحصائيات البوت:\n\n"
        f"👥 المستخدمين: {total}\n"
        f"✅ أكملوا: {completed}\n"
        f"❌ لم يكملوا: {total - completed}\n"
        f"💰 Coins موزعة: {completed * 100}"
    )

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 البوت شغال!")
    app.run_polling()

if _name_ == "_main_":
    main()
