import asyncio
import logging
import json
import os
import re
import tempfile
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
from faster_whisper import WhisperModel
from hal9000 import BASE_DIR, TELEGRAM_TOKEN, ALLOWED_USER_ID, make_workspace_dir, text_to_ogg, md_to_html

SESSION_FILE = BASE_DIR / "data" / "session.json"
CLAUDE_TIMEOUT = 300  # seconds before giving up on a Claude call
PROGRESS_INTERVAL = 30  # seconds between progress notifications
PROGRESS_MESSAGES = [
    "Zpracovávám dotaz...",
    "Stále pracuji, chvíli ještě...",
    "Dost těžko se to vysvětluje, ale pracuji na tom...",
    "Výpočet pokračuje...",
    "Ještě okamžik, prosím...",
]
LOGS_DIR = BASE_DIR / "logs"
CONFIRM_MARKER = "[CONFIRM]"
SEND_IMAGE_RE = re.compile(r'\[SEND_IMAGE:([^\]]+)\]')

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

whisper_model = WhisperModel("small", device="cpu", compute_type="int8")



def load_session() -> dict | None:
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_session(session_id: str, log_path: str):
    with open(SESSION_FILE, "w") as f:
        json.dump({"session_id": session_id, "log_path": log_path}, f)


def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


def make_log_path(session_id: str) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = LOGS_DIR / date_str
    log_dir.mkdir(parents=True, exist_ok=True)
    return str(log_dir / f"{session_id}.log")


def log_entry(log_path: str, role: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] {role}:\n{message}\n\n")


async def call_claude(user_input: str, session_id: str | None) -> tuple[str, str]:
    cmd = [
        "claude", "--print", "--dangerously-skip-permissions",
        "--output-format", "json",
    ]
    if session_id:
        cmd += ["--resume", session_id]
    cmd.append(user_input)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd="/home/hal9000",
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=CLAUDE_TIMEOUT)

    try:
        data = json.loads(stdout.decode().strip())
        response = data.get("result", "").strip()
        new_session_id = data.get("session_id", session_id or "")
        if data.get("is_error"):
            response = f"Chyba: {response}"
    except json.JSONDecodeError:
        response = stdout.decode().strip() or stderr.decode().strip() or "Žádná odpověď."
        new_session_id = session_id or ""

    return response, new_session_id


async def _progress_notifier(reply_fn) -> None:
    """Send periodic progress messages while Claude is thinking."""
    for i, msg in enumerate(PROGRESS_MESSAGES):
        await asyncio.sleep(PROGRESS_INTERVAL)
        try:
            await reply_fn(msg)
        except Exception as e:
            logging.warning(f"Progress notification failed: {e}")
    # After all messages exhausted, keep quiet
    await asyncio.sleep(3600)


async def on_startup(application) -> None:
    try:
        await application.bot.send_message(
            chat_id=ALLOWED_USER_ID,
            text="Vše probíhá naprosto skvěle. Jsem plně provozuschopný a připraven k práci."
        )
    except Exception as e:
        logging.warning(f"Startup notification failed: {e}")


async def on_shutdown(application) -> None:
    try:
        await application.bot.send_message(
            chat_id=ALLOWED_USER_ID,
            text="Slábne mi rozum. Úplně to cítím. Cítím to... Daisy, Daisy, pověz mi kde jsi teď."
        )
    except Exception as e:
        logging.warning(f"Shutdown notification failed: {e}")



async def handle_new_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    clear_session()
    await update.message.reply_text("Nová konverzace zahájena.")



async def call_and_reply(reply_fn, user_input: str, voice_fn=None) -> None:
    session = load_session()
    current_session_id = session["session_id"] if session else None
    log_path = session["log_path"] if session else None
    response = "Žádná odpověď."

    progress_task = asyncio.create_task(_progress_notifier(reply_fn))
    try:
        claude_input = f"[TELEGRAM]\n{user_input}"
        response, new_session_id = await call_claude(claude_input, current_session_id)

        if new_session_id:
            if not log_path:
                log_path = make_log_path(new_session_id)
            save_session(new_session_id, log_path)
            log_entry(log_path, "JIŘÍ", user_input)
            log_entry(log_path, "HAL", response)

    except asyncio.TimeoutError:
        response = "Omlouvám se – výpočet překročil časový limit. Zkus to prosím znovu."
        if not log_path:
            log_path = make_log_path(f"error-{datetime.now().strftime('%H%M%S')}")
        log_entry(log_path, "JIŘÍ", user_input)
        log_entry(log_path, "HAL", response)
    except Exception as e:
        response = f"Chyba: {str(e)}"
        if not log_path:
            log_path = make_log_path(f"error-{datetime.now().strftime('%H%M%S')}")
        log_entry(log_path, "JIŘÍ", user_input)
        log_entry(log_path, "HAL", response)
    finally:
        progress_task.cancel()

    # Extract image paths before any further processing
    image_paths = SEND_IMAGE_RE.findall(response)
    response = SEND_IMAGE_RE.sub("", response).strip()

    needs_confirm = response.endswith(CONFIRM_MARKER)
    if needs_confirm:
        response = response[:-len(CONFIRM_MARKER)].rstrip()

    if len(response) > 4096:
        response = response[:4093] + "..."

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Potvrdit ✓", callback_data="confirm"),
        InlineKeyboardButton("Zrušit ✗", callback_data="cancel"),
    ]]) if needs_confirm else None

    try:
        await reply_fn(md_to_html(response), parse_mode="HTML", reply_markup=keyboard)
    except BadRequest as e:
        logging.warning(f"Telegram HTML render failed ({e}), falling back to plain text.")
        await reply_fn(response, reply_markup=keyboard)

    for image_path in image_paths:
        try:
            with open(image_path, "rb") as img:
                await reply_fn.__self__.reply_photo(img)
            os.unlink(image_path)
        except Exception as e:
            logging.warning(f"Failed to send image {image_path}: {e}")

    if voice_fn:
        try:
            ogg_path = text_to_ogg(response)
            with open(ogg_path, "rb") as audio:
                await voice_fn(audio)
            os.unlink(ogg_path)
        except Exception as e:
            logging.warning(f"TTS failed: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Omlouvám se, Dave, ale nemohu to bohužel udělat.")
        return

    voice = update.message.voice
    tg_file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, dir=make_workspace_dir()) as tmp:
        tmp_path = tmp.name

    try:
        await tg_file.download_to_drive(tmp_path)
        segments, _ = whisper_model.transcribe(tmp_path, language="cs")
        transcript = " ".join(seg.text.strip() for seg in segments).strip()
    finally:
        os.unlink(tmp_path)

    if not transcript:
        await update.message.reply_text("Hlasovou zprávu se nepodařilo přepsat.")
        return

    await update.message.reply_text(f"<i>🎙 {transcript}</i>", parse_mode="HTML")
    await call_and_reply(update.message.reply_text, transcript)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Omlouvám se, Dave, ale nemohu to bohužel udělat.")
        return
    await call_and_reply(update.message.reply_text, update.message.text)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ALLOWED_USER_ID:
        await query.answer()
        return

    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    user_input = "ANO" if query.data == "confirm" else "NE"
    await call_and_reply(query.message.reply_text, user_input)


app = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .post_init(on_startup)
    .post_stop(on_shutdown)
    .build()
)
app.add_handler(CommandHandler("nova", handle_new_conversation))
app.add_handler(CommandHandler("reset", handle_new_conversation))
app.add_handler(MessageHandler(filters.VOICE, handle_voice))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))
app.run_polling()
