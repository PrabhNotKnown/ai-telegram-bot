# ------------------ Imports ------------------ #
import os
import uuid
import asyncio
import requests
import re
import yfinance as yf
import fitz  # PyMuPDF
import csv
import pyttsx3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

# ------------------ Load API Keys ------------------ #
TOKEN = os.getenv("BOT_TOKEN")
from groq import Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ------------------ Telegram States ------------------ #
ASK_TYPE, ASK_SYMBOL, ASK_PRICE = range(3)
ASK_URL, ASK_PROMPT, ASK_PDF, ASK_EMAIL_URL, ASK_EMAIL_FORMAT, ASK_PDF_OPTION, ASK_TEXT_FOR_VOICE = range(3, 10)

# ------------------ Init Bot App ------------------ #
app = ApplicationBuilder().token(TOKEN).build()

# ------------------ Error & Fallback ------------------ #
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[ERROR] Update: {update}, Error: {context.error}")
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ Unexpected error occurred. Please try again.")

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Invalid input. Please follow the steps or type /help.")

# ------------------ /start /help /cancel ------------------ #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Type /help to see everything I can do.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Welcome message\n"
        "/help - List commands\n"
        "/setalert - Price alert\n"
        "/summary - Web summary\n"
        "/summarizepdf - PDF summary (summary/fulltext/audio)\n"
        "/pdftovoice - PDF or Text to Voice\n"
        "/extractemails - Extract emails\n"
        "/cancel - Cancel operation"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Canceled.")
    return ConversationHandler.END

# ------------------ Set Alert (Crypto Only) ------------------ #
SYMBOL_TO_ID = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana", "bnb": "binancecoin"
}

async def setalert_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔤 Enter coin symbol (e.g., btc, eth):")
    return ASK_SYMBOL

async def setalert_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.lower()
    if symbol not in SYMBOL_TO_ID:
        await update.message.reply_text("❌ Symbol not supported. Try btc, eth, sol, bnb.")
        return ASK_SYMBOL
    context.user_data["symbol"] = symbol
    await update.message.reply_text(f"💰 Enter target price for {symbol.upper()}:")
    return ASK_PRICE

async def setalert_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        symbol = context.user_data["symbol"]
        context.application.create_task(alert_checker(update.effective_chat.id, symbol, price, context))
        await update.message.reply_text(f"✅ Alert set for {symbol.upper()} at ${price}")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Enter a valid number.")
        return ASK_PRICE

async def alert_checker(chat_id, symbol, target, context):
    coin_id = SYMBOL_TO_ID[symbol]
    while True:
        try:
            res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd")
            price = res.json()[coin_id]["usd"]
            if price >= target:
                await context.bot.send_message(chat_id=chat_id, text=f"🚨 {symbol.upper()} has reached ${price}!")
                break
        except Exception as e:
            print("[ALERT CHECK ERROR]", e)
        await asyncio.sleep(30)

# ------------------ Summary ------------------ #

async def summary_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["url"] = update.message.text
    await update.message.reply_text("🧠 Send prompt (e.g. Summarize in 5 points):")
    return ASK_PROMPT

from urllib.parse import urlparse

async def summary_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌐 Send the website URL (basic sites only):")
    return ASK_URL

async def summary_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["url"] = update.message.text
    await update.message.reply_text("🧠 Send prompt (e.g. Summarize in 5 points):")
    return ASK_PROMPT

MAX_CHARS = 5000  # ~4000 tokens safe

async def summary_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data["url"]
    prompt = update.message.text

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text()
        print(f"[DEBUG] Extracted text length: {len(text)}")

        if len(text.strip()) == 0:
            await update.message.reply_text("❌ Couldn't extract any text.")
            return ConversationHandler.END

        # Truncate the long text
        short_text = text[:MAX_CHARS]

        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": f"{prompt}\n\n{short_text}"}]
        )
        reply = response.choices[0].message.content.strip()

        reply = re.sub(r"\*\*(.*?)\*\*", r"\1", reply)
        reply = re.sub(r"\*(.*?)\*", r"\1", reply)
        reply = re.sub(r"_(.*?)_", r"\1", reply)

        await update.message.reply_text(reply[:4000])

    except Exception as e:
        print("[SUMMARY REQUEST ERROR]", e)
        await update.message.reply_text("❌ GPT API failed. Try again or use a shorter page.")

    return ConversationHandler.END


# ------------------ Email Extractor ------------------ #
async def extract_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Send URL to extract emails:")
    return ASK_EMAIL_URL

async def extract_emails_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email_url"] = update.message.text
    await update.message.reply_text("📁 Choose format:", reply_markup=ReplyKeyboardMarkup([
        [KeyboardButton("📃 Plain Text"), KeyboardButton("📊 CSV File")]
    ], one_time_keyboard=True, resize_keyboard=True))
    return ASK_EMAIL_FORMAT

async def extract_emails_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data["email_url"]
    fmt = update.message.text
    try:
        html = requests.get(url).text
        text = BeautifulSoup(html, "html.parser").get_text()
        emails = list(set(re.findall(r"[\w.-]+@[\w.-]+", text)))
        if not emails:
            await update.message.reply_text("❌ No emails found.")
        elif "csv" in fmt.lower():
            filename = f"emails_{uuid.uuid4().hex}.csv"
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Email"])
                for email in emails:
                    writer.writerow([email])
                await update.message.reply_document(InputFile(filename), filename=filename, caption="📩 Here are the extracted emails.")
                os.remove(filename)
        else:
            await update.message.reply_text("\n".join(emails))
    except Exception as e:
            print("[EMAIL ERROR]", e)
            await update.message.reply_text("❌ Failed.")
    return ConversationHandler.END

# ------------------ PDF Summary ------------------ #
async def summarize_pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Send the PDF file.")
    return ASK_PDF

async def summarize_pdf_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document.mime_type != "application/pdf":
        await update.message.reply_text("❌ Please send a PDF.")
        return ConversationHandler.END
    file = await update.message.document.get_file()
    path = f"temp_{uuid.uuid4().hex}.pdf"
    await file.download_to_drive(path)
    context.user_data["pdf_path"] = path
    await update.message.reply_text("Choose option:", reply_markup=ReplyKeyboardMarkup([
        ["🧠 Summary", "📜 Full Text", "🔊 Audio"]
    ], one_time_keyboard=True, resize_keyboard=True))
    return ASK_PDF_OPTION

async def summarize_pdf_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    path = context.user_data["pdf_path"]
    text = "\n".join([page.get_text() for page in fitz.open(path)])[:5000]
    
    if "summary" in choice.lower():
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # recommended by Groq as of July 2025,
            messages=[
                {"role": "user", "content": f"Summarize this:\n\n{text}"}
            ]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply[:4000])
    
    elif "full" in choice.lower():
        await update.message.reply_text(text[:4000])
    
    elif "audio" in choice.lower():
        engine = pyttsx3.init()
        audio_file = f"{uuid.uuid4().hex}.mp3"
        engine.save_to_file(text[:1000], audio_file)
        engine.runAndWait()
        await update.message.reply_audio(InputFile(audio_file))
        os.remove(audio_file)

    os.remove(path)
    return ConversationHandler.END


# ------------------ Text to Voice ------------------ #
async def pdftovoice_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.document and update.message.document.mime_type == "application/pdf":
            file = await update.message.document.get_file()
            path = f"voice_{uuid.uuid4().hex}.pdf"
            await file.download_to_drive(path)
            text = "\n".join([page.get_text() for page in fitz.open(path)])
            os.remove(path)
        else:
            text = update.message.text

        engine = pyttsx3.init()
        audio_file = f"{uuid.uuid4().hex}.mp3"
        engine.save_to_file(text[:1000], audio_file)
        engine.runAndWait()
        await update.message.reply_audio(InputFile(audio_file))
        os.remove(audio_file)

    except Exception as e:
        print("[PDF to Voice ERROR]", e)
        await update.message.reply_text("❌ Could not process.")

# ------------------ /pdftovoice Entry ------------------ #
async def pdftovoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send text or PDF to convert into voice.")
    return ASK_TEXT_FOR_VOICE




# ------------------ Add Handlers ------------------ #
app.add_error_handler(error_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("setalert", setalert_start)],
    states={
        ASK_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, setalert_symbol)],
        ASK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setalert_price)],
    },
    fallbacks=[MessageHandler(filters.ALL, fallback_handler)]
))
app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("summary", summary_start)],
    states={
        ASK_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary_prompt)],
        ASK_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary_process)],
    },
    fallbacks=[MessageHandler(filters.ALL, fallback_handler)]
))
app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("extractemails", extract_emails_command)],
    states={
        ASK_EMAIL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_emails_url)],
        ASK_EMAIL_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_emails_format)],
    },
    fallbacks=[MessageHandler(filters.ALL, fallback_handler)]
))
app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("summarizepdf", summarize_pdf_start)],
    states={
        ASK_PDF: [MessageHandler(filters.Document.PDF, summarize_pdf_file)],
        ASK_PDF_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, summarize_pdf_process)],
    },
    fallbacks=[MessageHandler(filters.ALL, fallback_handler)]
))
app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("pdftovoice", pdftovoice)],
    states={
        ASK_TEXT_FOR_VOICE: [
            MessageHandler(filters.Document.PDF, pdftovoice_process),
            MessageHandler(filters.TEXT & ~filters.COMMAND, pdftovoice_process)
        ]
    },
    fallbacks=[MessageHandler(filters.ALL, fallback_handler)]
))

print("🤖 Bot is running...")
app.run_polling()
