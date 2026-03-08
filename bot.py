import os
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# الإعدادات الأساسية من بيئة التشغيل
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
CPA_LINK = os.environ.get("CPA_LINK", "https://passwordomain.com/1881602")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
WAIT_SECONDS = 30
DB_FILE = "users.json"

# وظائف قاعدة البيانات البسيطة (JSON)
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

# دالة البداية /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    # نظام الإحالة (Referral)
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        user_data = get_user(user_id)
        # التأكد أن المستخدم جديد ولم يسبق إحالته وأن المحيل ليس هو نفسه
        if user_data["referred_by"] is None and referrer_id != user_id:
            update_user(user_id, {"referred_by": referrer_id})

    get_user(user_id) # إنشاء الحساب إذا لم يكن موجوداً

    # إشعار للآدمين بدخول مستخدم جديد
    try:
        if ADMIN_ID != 0:
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
        f"🎮 بوت FF Rewards الرسمي\n\n"
        f"✅ أكمل مهمة واحدة واحصل على:\n"
        f"💎 100 Coins مجاناً\n"
        f"👥 50 Coins لكل صديق تدعوه\n\n"
        f"اختر من القائمة 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# معالج الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    await query.answer()

    if query.data == "get_coins":
        if user_data["completed_offer"]:
            await query.edit_message_text(
                f"✅ أكملت المهمة من قبل!\n💰 رصيدك الحالي: {user_data['coins']} Coins\n\n👥 ادعُ أصدقاء لتربح أكثر!"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔗 افتح الرابط وأكمل المهمة", url=CPA_LINK)],
                [InlineKeyboardButton("⏳ انتظر 30 ثانية...", callback_data="wait")]
            ]
            await query.edit_message_text(
                f"🎯 خطوة واحدة تفصلك عن الجائزة!\n\n"
                f"1️⃣ اضغط على الرابط بالأسفل\n"
                f"2️⃣ أكمل المهمة المطلوبة (CPA)\n"
                f"3️⃣ انتظر 30 ثانية في هذه الصفحة\n"
                f"4️⃣ سيظهر زر استلام الـ Coins تلقائياً!\n\n"
                f"💎 ستحصل على 100 Coins فوراً!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            update_user(user_id, {"timer_started": True})

            # الانتظار (سيتم تنفيذه في الخلفية للمستخدم الحالي فقط)
            await asyncio.sleep(WAIT_SECONDS)

            # التحقق مجدداً من حالة العرض
            current_data = get_user(user_id)
            if not current_data["completed_offer"]:
                keyboard_after = [
                    [InlineKeyboardButton("✅ خذ Coins ديالك!", callback_data="verify_offer")],
                ]
                try:
                    await query.edit_message_text(
                        f"⏰ انتهى وقت الانتظار!\n\n"
                        f"إذا أكملت المهمة بنجاح، اضغط على الزر أسفله لاستلام جائزتك 👇",
                        reply_markup=InlineKeyboardMarkup(keyboard_after)
                    )
                except:
                    pass

    elif query.data == "wait":
        await query.answer("⏳ يرجى الانتظار! سيظهر الزر بعد اكتمال الـ 30 ثانية.", show_alert=True)

    elif query.data == "verify_offer":
        user_data = get_user(user_id) # تحديث البيانات
        if not user_data["completed_offer"]:
            new_coins = user_data["coins"] + 100
            update_user(user_id, {
                "completed_offer": True,
                "coins": new_coins,
                "timer_started": False
            })

            # منح المكافأة للمحيل (Referrer)
            if user_data["referred_by"]:
                referrer_id = str(user_data["referred_by"])
                referrer_data = get_user(referrer_id)
                update_user(referrer_id, {
                    "coins": referrer_data["coins"] + 50,
                    "referrals": referrer_data["referrals"] + 1
                })
                try:
                    await context.bot.send_message(
                        chat_id=int(referrer_id),
                        text=f"🎉 صديقك أكمل المهمة بنجاح!\n💰 تم إضافة 50 Coins لرصيدك.\n💎 رصيدك الآن: {referrer_data['coins'] + 50} Coins"
                    )
                except Exception as e:
                    logging.error(f"Failed to notify referrer: {e}")

            # إشعار الآدمين
            try:
                if ADMIN_ID != 0:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"✅ مستخدم أكمل المهمة!\nID: {user_id}\n💰 رصيده أصبح: {new_coins}"
                    )
            except:
                pass

            await query.edit_message_text(
                f"🎉 تهانينا يا بطل!\n\n✅ تم إضافة 100 Coins لحسابك.\n💰 رصيدك الحالي: {new_coins} Coins\n\n👥 يمكنك ربح 50 Coins إضافية عن كل صديق تدعوه!"
            )

    elif query.data == "balance":
        await query.edit_message_text(
            f"💰 تفاصيل رصيدك:\n\n"
            f"💎 إجمالي الـ Coins: {user_data['coins']}\n"
            f"👥 عدد الإحالات: {user_data['referrals']}\n"
            f"💵 أرباح الدعوات: {user_data['referrals'] * 50} Coins"
        )

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(
            f"👥 نظام الإحالة:\n\n"
            f"🔗 رابطك الخاص:\n{ref_link}\n\n"
            f"💰 ستحصل على 50 Coins فور إكمال صديقك لمهمته الأولى!\n"
            f"👥 دعوت حتى الآن: {user_data['referrals']} أصدقاء"
        )

# أمر الإحصائيات للآدمين فقط
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    total = len(db)
    completed = sum(1 for u in db.values() if u.get("completed_offer"))
    await update.message.reply_text(
        f"📊 إحصائيات البوت الحالية:\n\n"
        f"👥 إجمالي المستخدمين: {total}\n"
        f"✅ الذين أكملوا العروض: {completed}\n"
        f"❌ لم يكملوا بعد: {total - completed}\n"
        f"💰 إجمالي Coins الموزعة: {completed * 100 + sum(u.get('referrals', 0)*50 for u in db.values())}"
    )

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TOKEN_HERE":
        print("❌ خطأ: BOT_TOKEN غير موجود!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 البوت شغال الآن على Railway...")
    app.run_polling()

if __name__ == "__main__":
    main()
