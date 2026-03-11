import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- التعديلات التي طلبتِها ---
BOT_TOKEN = "7864448553:AAF-U4Y8v5-qR5u4U9Vv5_T8" # ضعي التوكن الخاص بك هنا
ADMIN_ID = 1002341506 # الـ ID الخاص بك لاستقبال الطلبات
CPA_LINK = "https://passwordomain.com/1881602" # رابط الربح الخاص بك
# ---------------------------

WAIT_SECONDS = 30
DB_FILE = "users.json"

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

def get_user(user_id: str):
    db = load_db()
    if user_id not in db:
        db[user_id] = {
            "coins": 0,
            "completed_offer": False,
            "referrals": 0,
            "referred_by": None,
            "waiting_for_id": False,
            "timer_active": False
        }
        save_db(db)
    return db[user_id]

def update_user(user_id: str, data: dict):
    db = load_db()
    if user_id not in db:
        db[user_id] = {
            "coins": 0,
            "completed_offer": False,
            "referrals": 0,
            "referred_by": None,
            "waiting_for_id": False,
            "timer_active": False
        }
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

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 مستخدم جديد!\nالاسم: {user.first_name}\nالمعرف: {user_id}"
        )
    except:
        pass

    keyboard = [
        [InlineKeyboardButton("🎁 احصل على نقاطك مجاناً", callback_data="get_coins")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="referral")],
    ]
    await update.message.reply_text(
        f"🔥 مرحباً بك {user.first_name}!\n\n"
        f"🎮 بوت FF Rewards الرسمي\n\n"
        f"✅ أكمل مهمة واحدة فقط واحصل على:\n"
        f"💎 100 نقطة مجاناً\n"
        f"👥 50 نقطة لكل صديق تدعوه\n\n"
        f"اختر من القائمة أدناه 👇",
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
                f"✅ لقد أكملت المهمة مسبقاً!\n"
                f"💰 رصيدك الحالي: {user_data['coins']} نقطة\n\n"
                f"👥 ادعُ أصدقاءك لتحصل على المزيد!"
            )
            return

        if user_data.get("timer_active"):
            await query.answer("⏳ المهمة جارية! انتظر ظهور الزر.", show_alert=True)
            return

        keyboard = [
            [InlineKeyboardButton("🔗 افتح الرابط وأكمل المهمة", url=CPA_LINK)],
            [InlineKeyboardButton("⏳ جارٍ العد التنازلي...", callback_data="wait")]
        ]
        await query.edit_message_text(
            f"🎯 خطوة واحدة تفصلك عن الجائزة!\n\n"
            f"1️⃣ اضغط على الرابط أدناه\n"
            f"2️⃣ أكمل المهمة المطلوبة\n"
            f"3️⃣ انتظر 30 ثانية\n"
            f"4️⃣ سيظهر زر المكافأة تلقائياً!\n\n"
            f"⏱️ بدأ العد التنازلي...",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        update_user(user_id, {"timer_active": True})
        await asyncio.sleep(WAIT_SECONDS)

        if not get_user(user_id)["completed_offer"]:
            update_user(user_id, {"timer_active": False})
            keyboard_after = [
                [InlineKeyboardButton("✅ استلم نقاطك الآن!", callback_data="verify_offer")]
            ]
            try:
                await query.edit_message_text(
                    f"⏰ انتهى وقت الانتظار!\n\n"
                    f"إذا أكملت المهمة، اضغط على الزر أدناه 👇\n"
                    f"💎 100 نقطة في انتظارك!",
                    reply_markup=InlineKeyboardMarkup(keyboard_after)
                )
            except:
                pass

    elif query.data == "wait":
        await query.answer("⏳ انتظر! سيظهر الزر بعد 30 ثانية.", show_alert=True)

    elif query.data == "verify_offer":
        user_data = get_user(user_id)
        if user_data["completed_offer"]:
            await query.answer("✅ لقد استلمت مكافأتك مسبقاً!", show_alert=True)
            return

        update_user(user_id, {
            "completed_offer": True,
            "coins": user_data["coins"] + 100,
            "waiting_for_id": True,
            "timer_active": False
        })

        if user_data["referred_by"]:
            referrer_id = str(user_data["referred_by"])
            r_data = get_user(referrer_id)
            update_user(referrer_id, {
                "coins": r_data["coins"] + 50,
                "referrals": r_data["referrals"] + 1
            })
            try:
                await context.bot.send_message(
                    chat_id=int(referrer_id),
                    text=f"🎉 أكمل صديقك المهمة بنجاح!\n"
                         f"💰 تمت إضافة 50 نقطة إلى رصيدك!\n"
                         f"💎 رصيدك الحالي: {r_data['coins'] + 50} نقطة"
                )
            except:
                pass

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ مستخدم أكمل المهمة!\nالمعرف: {user_id}\n💰 النقاط: {user_data['coins'] + 100}"
            )
        except:
            pass

        await query.edit_message_text(
            f"🎉 تهانينا!\n\n"
            f"✅ تمت إضافة 100 نقطة إلى حسابك!\n\n"
            f"👇 أرسل معرّفك في Free Fire الآن لنقوم بشحن حسابك:"
        )

    elif query.data == "balance":
        await query.edit_message_text(
            f"💰 تفاصيل رصيدك:\n\n"
            f"💎 النقاط: {user_data['coins']}\n"
            f"👥 عدد المدعوين: {user_data['referrals']}\n"
            f"🎁 نقاط الدعوة: {user_data['referrals'] * 50} نقطة"
        )

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(
            f"👥 نظام الدعوة:\n\n"
            f"🔗 رابطك الخاص:\n{ref_link}\n\n"
            f"💰 ستحصل على 50 نقطة لكل صديق يكمل المهمة!\n"
            f"👥 عدد من دعوتهم: {user_data['referrals']}"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)

    if user_data.get("waiting_for_id"):
        ff_id = update.message.text
        update_user(user_id, {"waiting_for_id": False})

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🎮 طلب شحن جديد!\n"
                     f"👤 الاسم: {update.effective_user.first_name}\n"
                     f"🆔 تيليغرام: {user_id}\n"
                     f"🎯 معرف Free Fire: {ff_id}"
            )
        except:
            pass

        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        await update.message.reply_text(
            f"✅ تم استلام معرفك بنجاح: {ff_id}\n\n"
            f"🔥 سنقوم بمراجعة طلبك وشحن حسابك في أقرب وقت!\n\n"
            f"━━━━━━━━━━━━\n"
            f"💎 هل تريد المزيد من النقاط؟\n"
            f"شارك رابطك مع أصدقائك:\n"
            f"{ref_link}"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🎁 احصل على نقاطك مجاناً", callback_data="get_coins")],
            [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
            [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="referral")],
        ]
        await update.message.reply_text(
            "اختر من القائمة أدناه 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    total = len(db)
    completed = sum(1 for u in db.values() if u.get("completed_offer"))
    await update.message.reply_text(
        f"📊 إحصائيات البوت:\n\n"
        f"👥 إجمالي المستخدمين: {total}\n"
        f"✅ أكملوا المهمة: {completed}\n"
        f"❌ لم يكملوا بعد: {total - completed}\n"
        f"💰 إجمالي النقاط الموزعة: {completed * 100}"
    )

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 البوت يعمل الآن!")
    app.run_polling()

if __name__ == "__main__":
    main()
