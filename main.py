import asyncio
import html
import logging
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, KeyboardButton, ReplyKeyboardMarkup,
    WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.staticfiles import StaticFiles
import hmac
import hashlib

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("samarkand-date")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
ACCESS_CODE = os.getenv("ACCESS_CODE", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")
if not ADMIN_ID_RAW.isdigit():
    raise RuntimeError("ADMIN_ID must be a numeric Telegram user ID")
if len(ACCESS_CODE) < 4:
    raise RuntimeError("ACCESS_CODE must contain at least 4 characters")

ADMIN_ID = int(ADMIN_ID_RAW)
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# In-memory rate limit only. It resets when Railway restarts; no Volume/database.
last_submission = {}


class Submission(BaseModel):
    init_data: str = Field(min_length=1, max_length=8192)
    access_code: str = Field(min_length=1, max_length=100)
    answers: dict[str, str]


def verify_telegram_init_data(init_data: str) -> dict:
    """Validate Telegram Mini App initData using Telegram's HMAC procedure."""
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        if not received_hash:
            raise ValueError("Missing hash")

        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(pairs.items())
        )
        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            raise ValueError("Invalid Telegram signature")

        auth_date = int(pairs.get("auth_date", "0"))
        if auth_date <= 0 or abs(time.time() - auth_date) > 86400:
            raise ValueError("Expired Telegram session")

        import json
        user = json.loads(pairs.get("user", "{}"))
        if not isinstance(user, dict) or not user.get("id"):
            raise ValueError("Telegram user is missing")
        return user
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Telegram authorization failed") from exc


QUESTIONS = {
    "q1": "Какой формат встречи тебе ближе?",
    "q2": "Куда тебе было бы интереснее сходить в Самарканде?",
    "q3": "Какую атмосферу кафе ты предпочитаешь?",
    "q4": "Какая кухня тебе нравится?",
    "q5": "Что выберешь из напитков?",
    "q6": "В какое время удобнее встретиться?",
    "q7": "Какой вариант прогулки тебе интереснее?",
    "q8": "Какой бюджет на одного человека тебе комфортен?",
    "q9": "Какую музыку ты предпочитаешь?",
    "q10": "Какой формат общения тебе комфортнее?",
    "q11": "Сколько времени ты хотела бы выделить на встречу?",
    "q12": "Есть ли пожелания или идеи от тебя?"
}


@dp.message(CommandStart())
async def start_handler(message: Message):
    if not WEBAPP_URL.startswith("https://"):
        await message.answer("Mini App ещё настраивается. Попробуй позже.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Открыть SAMARKAND DATE",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])
    await message.answer(
        "Привет! Это небольшая анкета о предпочтениях для возможной встречи "
        "в Самарканде.\n\n"
        "Ответы будут отправлены владельцу этого бота. Заполняй анкету "
        "только если тебе комфортно. Можно закрыть приложение в любой момент.",
        reply_markup=keyboard
    )


@dp.message(F.text == "/help")
async def help_handler(message: Message):
    await message.answer("Нажми /start, чтобы открыть анкету SAMARKAND DATE.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    )
    log.info("Bot polling started")
    yield
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    await bot.session.close()


app = FastAPI(title="Samarkand Date Mini App", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/submit")
async def submit(payload: Submission):
    if not hmac.compare_digest(payload.access_code, ACCESS_CODE):
        raise HTTPException(status_code=403, detail="Неверный защитный код")

    user = verify_telegram_init_data(payload.init_data)
    user_id = int(user["id"])

    now = time.time()
    if now - last_submission.get(user_id, 0) < 30:
        raise HTTPException(status_code=429, detail="Подожди 30 секунд перед повторной отправкой")
    last_submission[user_id] = now

    # Only accept the 12 expected fields and limit each answer's length.
    clean_answers = {}
    for key, question in QUESTIONS.items():
        answer = str(payload.answers.get(key, "")).strip()
        if len(answer) > 500:
            raise HTTPException(status_code=400, detail="Один из ответов слишком длинный")
        clean_answers[key] = answer or "Не указано"

    first_name = html.escape(str(user.get("first_name", "Не указано"))[:100])
    username = html.escape(str(user.get("username", ""))[:100])
    user_line = f"@{username}" if username else "без username"
    header = (
        "📝 <b>НОВАЯ АНКЕТА — SAMARKAND DATE</b>\n"
        f"👤 Имя: {first_name}\n"
        f"🔗 Username: {user_line}\n"
        f"🆔 Telegram ID: <code>{user_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await bot.send_message(ADMIN_ID, header, parse_mode="HTML")

    # Keep messages comfortably below Telegram's message size limit.
    for start in (0, 6):
        lines = []
        items = list(QUESTIONS.items())[start:start + 6]
        for idx, (key, question) in enumerate(items, start=start + 1):
            answer = html.escape(clean_answers[key])
            lines.append(f"<b>{idx}. {html.escape(question)}</b>\n{answer}")
        await bot.send_message(
            ADMIN_ID, "\n\n".join(lines), parse_mode="HTML"
        )

    return {"ok": True, "message": "Ответы отправлены. Спасибо!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
