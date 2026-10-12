import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
DB_PATH = os.getenv("DB_PATH", "bot.db")
# Kamida 1 ta majburiy kanal bo'lsa, kanallar tagida doim chiqadigan link
INSTAGRAM_URL = os.getenv(
    "INSTAGRAM_URL",
    "https://www.instagram.com/codialuz?utm_source=ig_web_button_share_sheet&obrf=ZDNlZDc0MzIxNw==",
)
