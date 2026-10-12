import os

from dotenv import load_dotenv

from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
try:
    ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
    if any(value <= 0 for value in ADMIN_IDS):
        raise ValueError
except ValueError as exc:
    raise ValueError("ADMIN_IDS: admin ID raqamlarini vergul bilan ajratib yozing.") from exc
DB_PATH = str(BASE_DIR / os.getenv("DB_PATH", "bot.db"))
# Kamida 1 ta majburiy kanal bo'lsa, kanallar tagida doim chiqadigan link
INSTAGRAM_URL = os.getenv(
    "INSTAGRAM_URL",
    "https://www.instagram.com/codialuz?utm_source=ig_web_button_share_sheet&obrf=ZDNlZDc0MzIxNw==",
)


def validate_config():
    from aiogram.utils.token import validate_token
    try:
        validate_token(BOT_TOKEN)
    except Exception as exc:
        raise ValueError("BOT_TOKEN noto‘g‘ri yoki bo‘sh. .env fayliga BotFather bergan tokenni yozing.") from exc
    if not ADMIN_IDS:
        raise ValueError("ADMIN_IDS bo‘sh. .env fayliga admin Telegram ID raqamini yozing.")
    if urlparse(INSTAGRAM_URL).scheme not in {"http", "https"} or not urlparse(INSTAGRAM_URL).netloc:
        raise ValueError("INSTAGRAM_URL to‘liq https:// havola bo‘lishi kerak.")
