import asyncio
import logging
import json
import urllib.request
import urllib.error
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = "8844786783:AAGwR1CmnGXFrkRzrTlsrvUk31XX32yag-U"
GEMINI_API_KEY = "AQ.Ab8RN6KXUWc8O3td9G_lyqahHAdxRMVtOZh5mrAbIPAaVfK0xw"

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "videos"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

user_target = {}

def bottom_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🇫🇷 Français"), KeyboardButton("🇬🇧 English")],
            [KeyboardButton("🎬 Envoyer une vidéo")],
        ],
        resize_keyboard=True,
    )

def ask_gemini(prompt_text, lang):
    """Fonction ultra-légère pour interroger Gemini sans module externe"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    instruction = f"Traduis ou réponds en français de manière utile : {prompt_text}" if lang == "fr" else f"Translate or answer in English: {prompt_text}"
    
    data = {
        "contents": [{"parts": [{"text": instruction}]}]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Erreur de communication avec Gemini : {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bienvenue !\n\n"
        "🎬 Choisis une langue en bas ou envoie-moi directement ta vidéo / ton texte :",
        reply_markup=bottom_menu(),
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target = user_target.get(user_id, "fr")
    lang_label = "Français" if target == "fr" else "English"

    video = update.message.video or update.message.document
    if not video:
        return

    await update.message.reply_text(
        "⏳ Réception de la vidéo en cours, patiente quelques secondes...",
        reply_markup=bottom_menu()
    )

    user_dir = DOWNLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    output_file = user_dir / "original.mp4"

    try:
        tg_file = await context.bot.get_file(video.file_id)
        await tg_file.download_to_drive(custom_path=str(output_file))

        await asyncio.sleep(1)

        with open(output_file, "rb") as video_file:
            await update.effective_chat.send_video(
                video=video_file,
                caption=f"✅ **Vidéo bien reçue et traitée !**\n🎯 Langue : {lang_label}",
                reply_markup=bottom_menu()
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Erreur : {str(e)[:150]}",
            reply_markup=bottom_menu()
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or ""

    if "Français" in text:
        user_target[user_id] = "fr"
        await update.message.reply_text(
            "🇫🇷 Langue définie sur le Français.\n🎬 Envoie ta vidéo !",
            reply_markup=bottom_menu(),
        )
        return
    elif "English" in text:
        user_target[user_id] = "en"
        await update.message.reply_text(
            "🇧 Language set to English.\n🎬 Send your video!",
            reply_markup=bottom_menu(),
        )
        return
    elif "Envoyer" in text:
        await update.message.reply_text(
            "🎬 Envoie ton fichier MP4 directement dans le chat.",
            reply_markup=bottom_menu(),
        )
        return

    target_lang = user_target.get(user_id, "fr")
    await update.message.chat.send_action("typing")

    # Appel de l'IA sans module externe
    loop = asyncio.get_running_loop()
    reply_text = await loop.run_in_executor(None, ask_gemini, text, target_lang)
    
    await update.message.reply_text(reply_text, reply_markup=bottom_menu())

def main():
    logging.basicConfig(level=logging.WARNING)
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN manquant.")

    print("🤖 Démarrage du bot sans erreur de module...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Bot prêt et en écoute !")
    app.run_polling()

if __name__ == "__main__":
    main()
