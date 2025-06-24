# bot.py
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, MessageHandler, Filters, CallbackContext,
    CommandHandler, CallbackQueryHandler, ConversationHandler
)
from cv_processor import extract_cv_info
from graphql_client import send_to_graphql
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ASK_JOB, ASK_COUNTRY, ASK_CITY, ASK_LEVEL, SHOW_MATCHES = range(5)

with open("job_offers.json", encoding="utf-8") as f:
    JOB_OFFERS = json.load(f)

def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Welcome! Please send your CV (PDF, DOCX, or TXT).")
    return ConversationHandler.END

def handle_document(update: Update, context: CallbackContext):
    file = update.message.document
    file_id = file.file_id
    new_file = context.bot.get_file(file_id)
    filename = os.path.join(DOWNLOAD_DIR, file.file_name)
    new_file.download(filename)

    update.message.reply_text("📄 CV received. Processing...")

    cv_info = extract_cv_info(filename)
    context.user_data["cv"] = cv_info

    if not cv_info.get("email"):
        update.message.reply_text("❌ Could not extract a valid email from the CV. Please ensure your CV includes your email address.")
        return ConversationHandler.END

    send_to_graphql(cv_info)

    update.message.reply_text("✅ CV processed. Let's find you a job!")
    update.message.reply_text("What job are you looking for?")
    return ASK_JOB

def ask_country(update: Update, context: CallbackContext):
    context.user_data["job"] = update.message.text
    keyboard = [[
        InlineKeyboardButton("🇫🇷 France", callback_data="France"),
        InlineKeyboardButton("🇩🇪 Germany", callback_data="Germany")
    ]]
    update.message.reply_text("In which country?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_COUNTRY

def ask_city(update: Update, context: CallbackContext):
    context.user_data["country"] = update.callback_query.data
    update.callback_query.answer()
    update.callback_query.message.reply_text("Which city?")
    return ASK_CITY

def ask_level(update: Update, context: CallbackContext):
    context.user_data["city"] = update.message.text
    update.message.reply_text("What is your experience level? (Junior, Mid, Senior)")
    return ASK_LEVEL

def show_matches(update: Update, context: CallbackContext):
    context.user_data["level"] = update.message.text.lower()
    job = context.user_data["job"].lower()
    country = context.user_data["country"].lower()
    city = context.user_data["city"].lower()
    level = context.user_data["level"]

    matches = [
        offer for offer in JOB_OFFERS
        if job in offer["title"].lower()
        and country in offer["location"].lower()
        and city in offer["location"].lower()
        and level in offer["level"].lower()
    ]

    if not matches:
        update.message.reply_text("❌ No matching offers found.")
        return ConversationHandler.END

    for offer in matches:
        text = f"**{offer['title']}**\nCompany: {offer['company']}\nLocation: {offer['location']}\nLevel: {offer['level']}\n\n{offer['description']}"
        keyboard = [[
            InlineKeyboardButton("✅ Apply", url=offer["url"]),
            InlineKeyboardButton("❌ Skip", callback_data="skip")
        ]]
        update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    return ConversationHandler.END

def skip(update: Update, context: CallbackContext):
    update.callback_query.answer()
    update.callback_query.message.reply_text("✅ Skipped.")
    return ConversationHandler.END

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.document, handle_document)],
        states={
            ASK_JOB: [MessageHandler(Filters.text & ~Filters.command, ask_country)],
            ASK_COUNTRY: [CallbackQueryHandler(ask_city)],
            ASK_CITY: [MessageHandler(Filters.text & ~Filters.command, ask_level)],
            ASK_LEVEL: [MessageHandler(Filters.text & ~Filters.command, show_matches)],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)
    dp.add_handler(CallbackQueryHandler(skip, pattern="^skip$"))

    print("🤖 Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
