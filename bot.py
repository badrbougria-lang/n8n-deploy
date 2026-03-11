import os
import json
import logging
import asyncio
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
CPA_LINK = os.environ.get("CPA_LINK", "https://passwordomain.com/1881602")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
WAIT_SECONDS = 30
DB_FILE = "users.json"

RANKS = [
    (0, "🥉 مبتدئ"),
    (100, "🥈 متوسط"),
    (300, "🥇 متقدم"),
    (600, "💎 محترف"),
    (1000, "👑 أسطورة"),
]

def get_rank(coins):
    rank = RANKS[0][1]
    for threshold, name in RANKS:
        if coins >= threshold:
            rank = name
    return rank

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
            "timer_active": False,
            "last_daily": None,
            "name": ""
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
            "timer_active": False,
            "last_daily": None,
            "name": ""
        }
    db[user_id].update(data)
    save_db(db)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 احصل على Coins مجاناً", callback_data="get_coins")],
        [InlineKeyboardButton("🎰 السحب اليومي", callback_data="daily"),
         InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("🏆 المتصدرون", callback_data="leaderboard"),
         InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    if context.args and context.args[0].startswith("ref_"):
        referrer_id = context.args[0].replace("ref_", "")
        user_data = get_user(user_id)
        if user_data["referred_by"] is None and referrer_id != user_id:
            update_user(user_id, {"referred_by": referrer_id})

    update_user(user_id, {"name": user.first_name})

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 مستخدم جديد!\n🏷️ الاسم: {user.first_name}\n🆔 ID: {user_id}"
        )
    except:
        pass

    await update.message.reply_text(
        f"🔥 مرحباً بك {user.first_name}!\n\n"
        f"🎮 بوت FF Rewards الرسمي 💎\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ أكمل مهمة واحدة واحصل على 100 Coins\n"
        f"👥 ادعُ صديق واربح 50 Coins إضافية\n"
        f"🎰 سحب يومي مجاني كل 24 ساعة!\n"
        f"🏆 تنافس مع الآخرين في Leaderboard!\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"اختر من القائمة أدناه 👇",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    await query.answer()

    if query.data == "get_coins":
        if user_data["completed_offer"]:
            rank = get_rank(user_data["coins"])
            await query.edit_message_text(
                f"✅ أكملت المهمة مسبقاً!\n\n"
                f"💰 رصيدك: {user_data['coins']} Coins\n"
                f"🏅 رتبتك: {rank}\n\n"
                f"👥 ادعُ أصدقاءك لتربح المزيد!",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
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
            f"4️⃣ سيظهر زر المكافأة تلقائياً! 🎁\n\n"
            f"⏱️ بدأ العد التنازلي...",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        update_user(user_id, {"timer_active": True})
        await asyncio.sleep(WAIT_SECONDS)

        if not get_user(user_id)["completed_offer"]:
            update_user(user_id, {"timer_active": False})
            try:
                await query.edit_message_text(
                    f"⏰ انتهى وقت الانتظار!\n\n"
                    f"إذا أكملت المهمة، اضغط أدناه 👇\n"
                    f"💎 100 Coins في انتظارك!",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ استلم Coins الآن!", callback_data="verify_offer")]
                    ])
                )
            except:
                pass

    elif query.data == "wait":
        await query.answer("⏳ انتظر! سيظهر الزر بعد 30 ثانية.", show_alert=True)

    elif query.data == "verify_offer":
        user_data = get_user(user_id)
        if user_data["completed_offer"]:
            await query.answer("✅ استلمت مكافأتك مسبقاً!", show_alert=True)
            return

        new_coins = user_data["coins"] + 100
        update_user(user_id, {
            "completed_offer": True,
            "coins": new_coins,
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
                    text=f"🎉 أكمل صديقك المهمة!\n"
                         f"💰 ربحت 50 Coins!\n"
                         f"💎 رصيدك الآن: {r_data['coins'] + 50} Coins",
                    parse_mode="Markdown"
                )
            except:
                pass

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ مستخدم أكمل المهمة!\n🆔 ID: {user_id}\n💰 Coins: {new_coins}"
            )
        except:
            pass

        rank = get_rank(new_coins)
        await query.edit_message_text(
            f"🎉 تهانينا يا بطل!\n\n"
            f"✅ تمت إضافة 100 Coins لحسابك!\n"
            f"💰 رصيدك: {new_coins} Coins\n"
            f"🏅 رتبتك: {rank}\n\n"
            f"👇 أرسل ID ديال Free Fire ديالك الآن:",
            parse_mode="Markdown"
        )

    elif query.data == "daily":
        today = str(date.today())
        if user_data.get("last_daily") == today:
            await query.edit_message_text(
                f"⏰ سحبت جائزتك اليوم!\n\n"
                f"🔄 ارجع غداً للسحب مجدداً!\n"
                f"💰 رصيدك: {user_data['coins']} Coins",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )
        else:
            import random
            reward = random.choice([10, 20, 30, 50])
            new_coins = user_data["coins"] + reward
            update_user(user_id, {"coins": new_coins, "last_daily": today})
            rank = get_rank(new_coins)
            await query.edit_message_text(
                f"🎰 السحب اليومي!\n\n"
                f"🎊 ربحت اليوم: {reward} Coins!\n"
                f"💰 رصيدك الآن: {new_coins} Coins\n"
                f"🏅 رتبتك: {rank}\n\n"
                f"🔄 ارجع غداً للسحب مجدداً!",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

    elif query.data == "balance":
        rank = get_rank(user_data["coins"])
        next_rank = None
        for threshold, name in RANKS:
            if user_data["coins"] < threshold:
                next_rank = f"{name} ({threshold} Coins)"
                break
        await query.edit_message_text(
            f"💰 تفاصيل حسابك:\n\n"
            f"💎 الرصيد: {user_data['coins']} Coins\n"
            f"🏅 الرتبة: {rank}\n"
            f"👥 المدعوون: {user_data['referrals']} أصدقاء\n"
            f"🎁 من الدعوات: {user_data['referrals'] * 50} Coins\n"
            + (f"⬆️ الرتبة التالية: {next_rank}\n" if next_rank else "👑 أنت في أعلى رتبة!\n"),
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif query.data == "leaderboard":
        db = load_db()
        sorted_users = sorted(db.items(), key=lambda x: x[1].get("coins", 0), reverse=True)[:10]
        text = "🏆 قائمة المتصدرين:\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, udata) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = udata.get("name", "مجهول")
            coins = udata.get("coins", 0)
            rank = get_rank(coins)
            text += f"{medal} {name} - {coins} Coins {rank}\n"
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(
            f"👥 نظام الدعوة:\n\n"
            f"🔗 رابطك الخاص:\n`{ref_link}`\n\n"
            f"💰 50 Coins لكل صديق يكمل المهمة!\n"
            f"👥 دعوت حتى الآن: {user_data['referrals']} أصدقاء\n"
            f"💵 مجموع أرباح الدعوات: {user_data['referrals'] * 50} Coins",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
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
                     f"🆔 Telegram: {user_id}\n"
                     f"🎯 FF ID: {ff_id}",
                parse_mode="Markdown"
            )
        except:
            pass

        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        await update.message.reply_text(
            f"✅ تم استلام ID ديالك: {ff_id}\n\n"
            f"🔥 سنراجع طلبك ونشحن حسابك قريباً!\n\n"
            f"━━━━━━━━━━━━\n"
            f"💎 بغيتي تربح أكثر؟\n"
            f"شارك رابطك مع أصدقائك:\n`{ref_link}`",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    else:
        await update.message.reply_text(
            "اختر من القائمة 👇",
            reply_markup=main_keyboard()
        )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    total = len(db)
    completed = sum(1 for u in db.values() if u.get("completed_offer"))
    total_coins = sum(u.get("coins", 0) for u in db.values())
    await update.message.reply_text(
        f"📊 إحصائيات البوت:\n\n"
        f"👥 المستخدمين: {total}\n"
        f"✅ أكملوا المهمة: {completed}\n"
        f"❌ لم يكملوا: {total - completed}\n"
        f"💰 Coins الموزعة: {total_coins}",
        parse_mode="Markdown"
    )

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 البوت شغال!")
    app.run_polling()

if _name_ == "_main_":
    main()
