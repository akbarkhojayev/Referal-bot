import html

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

import database as db

OK_STATUSES = {
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.RESTRICTED,
}


async def not_subscribed_channels(bot: Bot, user_id: int):
    """Foydalanuvchi a'zo bo'lmagan majburiy kanallar ro'yxati."""
    missing = []
    for ch in await db.get_channels():
        try:
            member = await bot.get_chat_member(ch["chat_id"], user_id)
            if member.status not in OK_STATUSES:
                missing.append(ch)
        except Exception:
            # Bot kanalda admin bo'lmasa yoki kanal o'chgan bo'lsa — tekshirib bo'lmaydi
            missing.append(ch)
    return missing


def user_mention(row) -> str:
    name = html.escape(row["full_name"] or str(row["id"]))
    if row["username"]:
        return f"{name} (@{row['username']})"
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
    except Exception:
        pass

    if user["referrer_id"]:
        refs = await db.referral_count(user["referrer_id"])
        try:
            await bot.send_message(
                user["referrer_id"],
                f"➖ Siz taklif qilgan {user_mention(user)} kanaldan chiqib ketdi, "
                f"ovozi bekor qilindi.\nJami taklif qilganlaringiz: <b>{refs}</b>",
            )
        except Exception:
            pass
    return True
