from aiogram import Bot, Router
from aiogram.filters import IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

import database as db
from utils import revoke_vote

router = Router()


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER))
async def left_channel(event: ChatMemberUpdated, bot: Bot):
    """Majburiy kanaldan chiqqan foydalanuvchi ovozi -1 bo'ladi.
    Ishlashi uchun bot kanalda admin bo'lishi kerak."""
    channel = await db.get_channel_by_chat(event.chat.id)
    if channel is None:
        return
    # Bazadagi voted sharti takroriy hodisada yana -1 bo‘lishiga yo‘l qo‘ymaydi.
    await revoke_vote(bot, event.new_chat_member.user.id, channel["title"])
