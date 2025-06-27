# bot.py
import os
import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler, filters, ContextTypes,
    CommandHandler, CallbackQueryHandler, ConversationHandler
)
from dotenv import load_dotenv
from cv_processor import extract_cv_info
from graphql_client import send_to_graphql
from job_fetcher import fetch_jobs

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Conversation states
ASK_JOB, ASK_COUNTRY, ASK_CITY, ASK_LEVEL, SHOW_MATCHES = range(5)

# File constraints
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.doc', '.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
MAX_FILE_SIZE = 20 * 1024 * 1024


# ✅ CANCELLATION HANDLER
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (
        "👋 Welcome to the Job Matching Bot!\n\n"
        "Send your CV (PDF, DOCX, DOC, TXT, or clear image).\n"
        "Then I’ll ask you a few questions and show job offers in France 🇫🇷 or Germany 🇩🇪\n"
        "📏 Max file size: 20MB"
    )
    await update.message.reply_text(text)
    return ConversationHandler.END


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        file = update.message.document
        file_ext = os.path.splitext(file.file_name)[1].lower()

        if file_ext not in SUPPORTED_EXTENSIONS:
            await update.message.reply_text("❌ Unsupported file format.")
            return ConversationHandler.END

        if file.file_size > MAX_FILE_SIZE:
            await update.message.reply_text("❌ File too large.")
            return ConversationHandler.END

        file_obj = await context.bot.get_file(file.file_id)
        filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}_{file.file_name}")
        await file_obj.download_to_drive(filename)

        await update.message.reply_text("📄 Processing your CV...")
        cv_info = extract_cv_info(filename)
        os.remove(filename)

        if not cv_info.get("email"):
            await update.message.reply_text("❌ Couldn’t extract a valid email.")
            return ConversationHandler.END

        context.user_data["cv"] = cv_info
        send_to_graphql(cv_info)

        await update.message.reply_text(
            f"✅ CV processed!\n\n👤 Name: {cv_info.get('name', 'N/A')}\n"
            f"📍 Location: {cv_info.get('location', 'Unknown')}\n"
            f"💼 Now, what job title are you looking for?"
        )
        return ASK_JOB

    except Exception as e:
        logger.error(f"CV Error: {e}")
        await update.message.reply_text("❌ Error processing your CV.")
        return ConversationHandler.END



async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        photo = update.message.photo[-1]
        file_obj = await context.bot.get_file(photo.file_id)
        filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}_cv.jpg")
        await file_obj.download_to_drive(filename)

        await update.message.reply_text("🖼️ Processing image CV...")
        cv_info = extract_cv_info(filename)
        os.remove(filename)

        if not cv_info.get("email"):
            await update.message.reply_text("❌ Couldn’t extract email from the image.")
            return ConversationHandler.END

        context.user_data["cv"] = cv_info
        send_to_graphql(cv_info)

        await update.message.reply_text("✅ CV image processed!\n\nWhat job are you looking for?")
        return ASK_JOB

    except Exception as e:
        logger.error(f"Photo CV Error: {e}")
        await update.message.reply_text("❌ Error with image.")
        return ConversationHandler.END


async def ask_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["job"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("🇫🇷 France", callback_data="fr")],
        [InlineKeyboardButton("🇩🇪 Germany", callback_data="de")]
    ]
    await update.message.reply_text("Which country?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_COUNTRY


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["country"] = query.data

    await query.edit_message_text("Which city? Type 'any' for all.")
    return ASK_CITY


async def ask_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["city"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("👶 Junior", callback_data="junior"),
         InlineKeyboardButton("👨‍💼 Mid", callback_data="mid"),
         InlineKeyboardButton("🎯 Senior", callback_data="senior")]
    ]
    await update.message.reply_text("Your experience level?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_LEVEL


async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["level"] = query.data

    job = context.user_data["job"]
    country = context.user_data["country"]
    city = context.user_data["city"]
    level = context.user_data["level"]

    await query.edit_message_text("🔍 Searching jobs...")

    try:
        results = await fetch_jobs(
            job_title=job,
            country=country,
            city=city,
            level=level
        )

        if not results:
            await query.message.reply_text("❌ No jobs found.")
            return ConversationHandler.END

        for job_offer in results:
            await send_job_offer(query.message, job_offer)

    except Exception as e:
        logger.error(f"Adzuna fetch error: {e}")
        await query.message.reply_text("⚠️ Error fetching jobs.")

    return ConversationHandler.END


async def send_job_offer(message, job: Dict[str, Any]):
    title = job.get("title", "N/A")

    company = job.get("company", "Unknown")
    location = job.get("location", "Unknown")


    location_data = job.get("location")
    if isinstance(location_data, dict):
        location = location_data.get("display_name", "Unknown")
    else:
        location = "Unknown"

    url = job.get("url", "#")
    description = job.get("description", "")[:300] + "..."

    text = f"📌 *{title}* at *{company}*\n📍 {location}\n\n📝 {description}"
    keyboard = [[InlineKeyboardButton("Apply Now", url=url)]]

    await message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Document.ALL, handle_document),
            MessageHandler(filters.PHOTO, handle_photo)
        ],
        states={
            ASK_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_country)],
            ASK_COUNTRY: [CallbackQueryHandler(ask_city)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_level)],
            ASK_LEVEL: [CallbackQueryHandler(show_matches)]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
