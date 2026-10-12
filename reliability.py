import asyncio
import logging
import weakref

from aiogram import BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import ErrorEvent

from utils import SubscriptionCheckError

logger = logging.getLogger(__name__)


class UserLockMiddleware(BaseMiddleware):
    """Bir foydalanuvchining parallel yangilanishlarini tartib bilan bajaradi."""

    def __init__(self):
        self.locks = weakref.WeakValueDictionary()

    async def __call__(self, handler, event, data):
        update = data.get("event_update", event)
        member = getattr(update, "chat_member", None)
        user = member.new_chat_member.user if member else data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        lock = self.locks.setdefault(user.id, asyncio.Lock())
        async with lock:
            return await handler(event, data)


class RateLimitMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        for attempt in range(3):
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as exc:
                if attempt == 2:
                    raise
                await asyncio.sleep(exc.retry_after + 0.1)


async def handle_error(event: ErrorEvent, bot):
    exc = event.exception
    if isinstance(exc, SubscriptionCheckError):
        text = str(exc)
    else:
        logger.error("Yangilanishni qayta ishlashda xatolik", exc_info=(type(exc), exc, exc.__traceback__))
        text = "⚠️ Amalni bajarishda xatolik yuz berdi. Birozdan so‘ng qayta urinib ko‘ring yoki /start bosing."
    call = event.update.callback_query
    message = event.update.message
    try:
        if call:
            await call.answer(text, show_alert=True)
        elif message:
            await message.answer(text)
    except TelegramAPIError:
        if call and call.message:
            try:
                await bot.send_message(call.message.chat.id, text)
            except TelegramAPIError:
                logger.warning("Xatolik haqida xabar yetkazilmadi")
        else:
            logger.warning("Xatolik haqida xabar yetkazilmadi")
    return True
