import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import database as db
from config import BOT_TOKEN
from handlers import admin, channel, user


async def main():
    logging.basicConfig(level=logging.INFO)
    await db.init_db()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    # Admin router birinchi — admin xabarlari avval u yerda tekshiriladi
    dp.include_routers(admin.router, channel.router, user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    # chat_member yangilanishlari (kanaldan chiqish) kelishi uchun
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
