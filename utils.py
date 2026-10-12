import html
import logging

from aiogram.exceptions import TelegramAPIError

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

import database as db

OK_STATUSES = {
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
}


class SubscriptionCheckError(Exception):
    """Obunani tekshirishning imkoni yo‘q; mavjud ovoz saqlanadi."""


def is_member(member):
    return member.status in OK_STATUSES or (
        member.status == ChatMemberStatus.RESTRICTED and member.is_member
    )


async def not_subscribed_channels(bot: Bot, user_id: int):
    """Foydalanuvchi a'zo bo'lmagan majburiy kanallar ro'yxati."""
    missing = []
    for ch in await db.get_channels():
        try:
            member = await bot.get_chat_member(ch["chat_id"], user_id)
            if not is_member(member):
                missing.append(ch)
        except TelegramAPIError as exc:
            logging.warning("Kanal obunasini tekshirib bo‘lmadi: %s", ch["chat_id"])
            raise SubscriptionCheckError(
                "Obunani hozir tekshirib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring. "
                "Muammo davom etsa, adminga murojaat qiling."
            ) from exc
    return missing


def user_mention(row) -> str:
    name = html.escape(row["full_name"] or str(row["id"]))
    if row["username"]:
        return f"{name} (@{html.escape(row['username'])})"
    return name


async def ref_link(bot: Bot, user_id: int) -> str:
    me = await bot.get_me()
    return f"https://t.me/{me.username}?start=r{user_id}"


async def group_link(bot: Bot, group_id: int) -> str:
    me = await bot.get_me()
    return f"https://t.me/{me.username}?start=g{group_id}"


async def revoke_vote(bot: Bot, user_id: int, reason_channel: str | None = None) -> bool:
    """Kanaldan chiqqan foydalanuvchining ovozini -1 qiladi va xabar beradi."""
    user = await db.get_user(user_id)
    if user is None or not await db.unvote(user_id):
        return False

    group = await db.get_group(user["group_id"])
    group_name = html.escape(group["name"]) if group else "guruh"
    where = f"<b>{html.escape(reason_channel)}</b> kanalidan" if reason_channel else "majburiy kanaldan"
    try:
        await bot.send_message(
            user_id,
            f"⚠️ Siz {where} chiqib ketdingiz, shuning uchun <b>{group_name}</b> "
            "guruhiga bergan ovozingiz bekor qilindi (-1).\n"
            "Qayta a'zo bo'lib /start bossangiz, ovozingiz qaytadi.",
        )
    except TelegramAPIError:
        logging.warning("Foydalanuvchiga bildirishnoma yetkazilmadi: %s", user_id)

    if user["referrer_id"]:
        refs = await db.referral_count(user["referrer_id"])
        try:
            await bot.send_message(
                user["referrer_id"],
                f"➖ Siz taklif qilgan {user_mention(user)} kanaldan chiqib ketdi, "
                f"ovozi bekor qilindi.\nJami taklif qilganlaringiz: <b>{refs}</b>",
            )
        except TelegramAPIError:
            logging.warning("Taklifchiga bildirishnoma yetkazilmadi: %s", user["referrer_id"])
    return True


async def answer_lines(message, lines):
    """HTML satrlarini buzmasdan Telegram xabar limitiga mos yuboradi."""
    chunk = []
    size = 0
    for line in lines:
        if chunk and size + len(line) + 1 > 3800:
            await message.answer("\n".join(chunk))
            chunk, size = [], 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        await message.answer("\n".join(chunk))
