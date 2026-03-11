import os
import json
import logging
import asyncio
from datetime import date
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات الخاصة بكِ (المستخرجة من صورك) ---
BOT_TOKEN = "8642131917:AAFbaWFohwIH3wS6_ob3FKGR8fvl_dAk sB0" # التوكن الجديد
CPA_LINK = "https://passwordomain.com/1881602" # رابط الربح
ADMIN_ID = 1002341506 # الـ ID الخاص بكِ لاستلام الطلبات
# ----------------------------------------------

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
        db[user_id] = {"coins": 0, "completed_offer": False, "referrals": 0, "referred_by": None, "waiting_for_id": False, "timer_active": False, "last_daily": None, "name": ""}
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
        f"🔥 *مرحباً بك {user.first_name}!*\n\n"
        f"🎮 *بوت FF Rewards الرسمي* 💎\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ أكمل مهمة واحدة واحصل على *100 Coins*\n"
        f"👥 ادعُ صديق واربح *50 Coins* إضافية\n"
        f"🎰 سحب يومي مجاني كل 24 ساعة\n"
        f"🏆 تنافس مع الآخرين في Leaderboard\n"
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
                f"✅ *أكملت المهمة مسبقاً!*\n\n💰 رصيدك: *{user_data['coins']} Coins*\n🏅 رتبتك: {rank}",
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
        await query.edit_message_text(f"🎯 *خطوة واحدة تفصلك عن الجائزة!*\n\n⏱️ *بدأ العد التنازلي (30 ثانية)...*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

        update_user(user_id, {"timer_active": True})
        await asyncio.sleep(WAIT_SECONDS)
        update_user(user_id, {"timer_active": False})

        await query.edit_message_text(
            f"⏰ *انتهى وقت الانتظار!*\n\nإذا أكملت المهمة اضغط أدناه 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ استلم Coins الآن!", callback_data="verify_offer")]])
        )

    elif query.data == "verify_offer":
        new_coins = user_data["coins"] + 100
        update_user(user_id, {"completed_offer": True, "coins": new_coins, "waiting_for_id": True})

        if user_data["referred_by"]:
            ref_id = str(user_data["referred_by"])
            r_db = load_db()
            if ref_id in r_db:
                update_user(ref_id, {"coins": r_db[ref_id]["coins"] + 50, "referrals": r_db[ref_id]["referrals"] + 1})

        await query.edit_message_text(f"🎉 *تهانينا!*\n\n💰 رصيدك: *{new_coins} Coins*\n👇 أرسل *ID ديال Free Fire* ديالك الآن:", parse_mode="Markdown")

    elif query.data == "daily":
        today = str(date.today())
        if user_data.get("last_daily") == today:
            await query.edit_message_text(f"⏰ *سحبت جائزتك اليوم!*\n💰 رصيدك: *{user_data['coins']} Coins*", parse_mode="Markdown", reply_markup=main_keyboard())
        else:
            reward = random.choice([10, 20, 30, 50])
            new_coins = user_data["coins"] + reward
            update_user(user_id, {"coins": new_coins, "last_daily": today})
            await query.edit_message_text(f"🎰 ربحت اليوم: *{reward} Coins*\n💰 رصيدك: *{new_coins} Coins*", parse_mode="Markdown", reply_markup=main_keyboard())

    elif query.data == "balance":
        rank = get_rank(user_data["coins"])
        await query.edit_message_text(f"💰 *رصيدك:* {user_data['coins']} Coins\n🏅 *الرتبة:* {rank}", parse_mode="Markdown", reply_markup=main_keyboard())

    elif query.data == "leaderboard":
        db = load_db()
        sorted_users = sorted(db.items(), key=lambda x: x[1].get("coins", 0), reverse=True)[:5]
        text = "🏆 *قائمة المتصدرين:*\n\n"
        for i, (uid, udata) in enumerate(sorted_users):
            text += f"{i+1}. {udata.get('name', 'مجهول')} - {udata.get('coins', 0)} Coins\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_keyboard())

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(f"👥 *رابطك الخاص:*\n`{ref_link}`\n\n💰 50 Coins لكل صديق!", parse_mode="Markdown", reply_markup=main_keyboard())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    if user_data.get("waiting_for_id"):
        ff_id = update.message.text
        update_user(user_id, {"waiting_for_id": False})
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🎮 طلب شحن جديد:\n🆔 Telegram: `{user_id}`\n🎯 FF ID: `{ff_id}`", parse_mode="Markdown")
        await update.message.reply_text(f"✅ تم استلام الـ ID: `{ff_id}`\nسيتم الشحن قريباً!", reply_markup=main_keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 البوت يعمل الآن!")
    app.run_polling()

if __name__ == "__main__":
    main()
