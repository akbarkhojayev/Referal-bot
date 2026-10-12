import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError

import database as db
from config import BOT_TOKEN, validate_config
from handlers import admin, channel, user
from reliability import RateLimitMiddleware, UserLockMiddleware, handle_error


async def main():
    validate_config()
    await db.init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.session.middleware(RateLimitMiddleware())
    dp = Dispatcher()
    dp.update.outer_middleware(UserLockMiddleware())
    dp.errors.register(handle_error)
    # Shaxsiy menyu va admin buyruqlari faqat botning shaxsiy chatida ishlaydi.
    for router in (admin.router, user.router):
        router.message.filter(F.chat.type == "private")
        router.callback_query.filter(F.message.chat.type == "private")
    dp.include_routers(admin.router, channel.router, user.router)
    try:
        while True:
            try:
                # Navbatdagi ovozlar va kanaldan chiqish hodisalarini saqlaymiz.
                await bot.delete_webhook(drop_pending_updates=False)
                await dp.start_polling(
                    bot, allowed_updates=dp.resolve_used_update_types(), close_bot_session=False
                )
                break
            except TelegramNetworkError:
                logging.warning("Telegram bilan aloqa uzildi. 5 soniyadan so‘ng qayta ulaniladi.")
                await asyncio.sleep(5)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (ValueError, sqlite3.Error) as exc:
        logging.error("Bot ishga tushmadi: %s", exc)
        raise SystemExit(1)
    except TelegramUnauthorizedError:
        logging.error("Bot tokeni yaroqsiz yoki bekor qilingan. .env dagi BOT_TOKEN ni yangilang.")
        raise SystemExit(1)
    except KeyboardInterrupt:
        logging.info("Bot to‘xtatildi.")
