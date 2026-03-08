import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # تأكدي أن رقمك محطوط في Railway Variables

users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"coins": 0, "referrals": 0, "waiting_for_screen": False}
    return users_db[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("✅ إتمام مهمة وإرسال سكرين", callback_data="send_proof")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 مرحباً بك! أتمم المهام وصيفط السكرين باش تاخد Coins:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id)

    if query.data == "send_proof":
        user_data["waiting_for_screen"] = True
        await query.edit_message_text("📸 من فضلك صيفط السكرين شوت (Screenshot) ديال المهمة دابا...")

    elif query.data == "balance":
        await query.edit_message_text(f"💰 رصيدك الحالي: {user_data['coins']} Coins")

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        await query.edit_message_text(f"🔗 رابط إحالتك:\n{ref_link}\n\nاربح 10 Coins على كل صديق!")

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if user_data.get("waiting_for_screen"):
        # إرسال الصورة للآدمين (أنتِ)
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"📩 إثبات جديد من المستخدم: {user_id}\nاليوزر: @{update.effective_user.username}"
        )
        
        user_data["waiting_for_screen"] = False
        await update.message.reply_text("✅ شكراً! تم إرسال السكرين للآدمين للمراجعة. غتوصل بنقاطك قريباً.")
    else:
        await update.message.reply_text("عفواً، استعمل القائمة أولاً لإرسال إثبات.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    # إضافة معالج الصور
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.run_polling()
