Import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# المعلومات الخاصة بكِ المدمجة في الكود
BOT_TOKEN = "ضع_التوكن_الخاص_بك_هنا" # احصلي عليه من BotFather وضعي هنا
ADMIN_ID = 1002341506  # الـ ID الخاص بكِ لاستقبال طلبات الشحن
CPA_LINK = "https://passwordomain.com/1880339" # رابط الربح الخاص بكِ
DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE,"r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE,"w") as f:
        json.dump(db,f)

def get_user(uid):
    db = load_db()
    if uid not in db:
        db[uid]={"coins":0,"referrals":0,"waiting":False}
        save_db(db)
    return db[uid]

def update_user(uid,data):
    db = load_db()
    if uid in db:
        db[uid].update(data)
        save_db(db)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    user=update.effective_user
    uid=str(user.id)
    get_user(uid)

    # التحقق من نظام الإحالة (Referral)
    args = context.args
    if args and args[0] != uid:
        referrer_id = args[0]
        db = load_db()
        if referrer_id in db and uid not in db: # إذا كان الشخص جديداً
            db[referrer_id]["coins"] += 50
            save_db(db)

    keyboard=[
        [InlineKeyboardButton("💎 شحن الجواهر",callback_data="coins")],
        [InlineKeyboardButton("💰 رصيدي الحالي",callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة الأصدقاء",callback_data="ref")]
    ]

    await update.message.reply_text(
        f"🔥 أهلاً بك يا {user.first_name}\n\nاجمع النقاط الآن واشحن جواهر فري فاير مجاناً!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    uid=str(query.from_user.id)
    data=get_user(uid)
    await query.answer()

    if query.data=="coins":
        keyboard=[[InlineKeyboardButton("🔗 اضغط هنا لإكمال المهمة",url=CPA_LINK)]]
        await query.edit_message_text(
            "⚠️ للتحقق من هويتك، يرجى إكمال المهمة في الرابط أدناه، ثم أرسل الـ ID الخاص بك هنا للحصول على 100 نقطة والشحن.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        update_user(uid,{"waiting":True})

    elif query.data=="balance":
        await query.edit_message_text(f"💰 رصيدك الحالي: {data['coins']} نقطة.")

    elif query.data=="ref":
        botname=(await context.bot.get_me()).username
        link=f"https://t.me/{botname}?start={uid}"
        await query.edit_message_text(
            f"شارك الرابط مع أصدقائك واحصل على 50 نقطة لكل صديق ينضم للبوت:\n\n{link}"
        )

async def text(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=str(update.effective_user.id)
    data=get_user(uid)

    if data.get("waiting"):
        ffid=update.message.text
        update_user(uid,{"waiting":False, "coins":data["coins"]+100})
        
        # إرسال إشعار لكِ فوراً بوجود ضحية/مستخدم أكمل المهمة
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚀 طلب شحن جديد\nالمستخدم: {uid}\nالـ ID المطلوب: {ffid}"
        )
        await update.message.reply_text("✅ تم استلام الـ ID بنجاح! سيتم التحقق من إكمال المهمة والشحن خلال ساعات.")

async def stats(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    db=load_db()
    await update.message.reply_text(f"📊 إحصائيات المشروع\n\nعدد المستخدمين: {len(db)}\nإجمالي النقاط الموزعة: {sum(u['coins'] for u in db.values())}")

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("stats",stats))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text))
    app.run_polling()

if __name__=="__main__":
    main()
