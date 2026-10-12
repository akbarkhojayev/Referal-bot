import asyncio
import html
import logging

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.enums import ChatType, ChatMemberStatus

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
from config import ADMIN_IDS
from utils import group_link, user_mention, answer_lines

router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


class AdminStates(StatesGroup):
    group_name = State()
    channel = State()
    broadcast = State()


@router.message(CommandStart())
@router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👑 Admin panel", reply_markup=kb.admin_menu)


@router.message(Command("cancel"))
@router.message(F.text == kb.BTN_CANCEL)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=kb.admin_menu)


# ---------- guruhlar ----------

@router.message(F.text == kb.BTN_ADD_GROUP)
async def add_group_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.group_name)
    await message.answer("Yangi guruh nomini yuboring:", reply_markup=kb.cancel_kb)


@router.message(AdminStates.group_name, F.text)
async def add_group_finish(message: Message, state: FSMContext, bot: Bot):
    name = message.text.strip()
    if not name or len(name) > 64:
        await message.answer("Guruh nomi 1 dan 64 tagacha belgidan iborat bo‘lsin.")
        return
    group_id = await db.add_group(name)
    await state.clear()
    link = await group_link(bot, group_id)
    await message.answer(
        f"✅ <b>{html.escape(name)}</b> guruhi qo'shildi.\n\n"
        f"Guruhning to'g'ridan-to'g'ri ovoz berish linki:\n{link}",
        reply_markup=kb.admin_menu,
    )


@router.message(F.text == kb.BTN_GROUPS)
async def list_groups(message: Message):
    groups = await db.groups_rating()
    if not groups:
        await message.answer("Guruhlar yo'q.")
        return
    await message.answer(
        "📋 Guruhlar (batafsil ko'rish uchun bosing):",
        reply_markup=kb.admin_groups_kb(groups),
    )


@router.callback_query(kb.AdminGroupCB.filter(F.action == "view"))
async def view_group(call: CallbackQuery, callback_data: kb.AdminGroupCB, bot: Bot):
    group = await db.get_group(callback_data.group_id)
    if group is None:
        await call.answer("Guruh topilmadi", show_alert=True)
        return
    votes = await db.group_votes(group["id"])
    top = await db.top_referrers(group["id"])
    link = await group_link(bot, group["id"])

    lines = [
        f"<b>{html.escape(group['name'])}</b>",
        f"Ovozlar: <b>{votes}</b>",
        f"Link: {link}",
        "",
        "🏆 Eng ko'p taklif qilganlar:",
    ]
    if top:
        lines += [f"{i}. {user_mention(u)} — {u['refs']}" for i, u in enumerate(top, 1)]
    else:
        lines.append("—")

    await call.message.answer(
        "\n".join(lines), reply_markup=kb.admin_group_detail_kb(group["id"])
    )
    await call.answer()


@router.callback_query(kb.AdminGroupCB.filter(F.action == "delete"))
async def delete_group(call: CallbackQuery, callback_data: kb.AdminGroupCB):
    await db.delete_group(callback_data.group_id)
    await call.message.edit_text("🗑 Guruh o'chirildi. Uning ovozchilari qayta ovoz bera oladi.")
    await call.answer()


# ---------- kanallar (shartlar) ----------

@router.message(F.text == kb.BTN_ADD_CHANNEL)
async def add_channel_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.channel)
    await message.answer(
        "Kanal username'ini (@kanal) yoki ID'sini (-100...) yuboring.\n"
        "❗ Bot o'sha kanalda <b>admin</b> bo'lishi shart.",
        reply_markup=kb.cancel_kb,
    )


@router.message(AdminStates.channel, F.text)
async def add_channel_finish(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()
    try:
        chat_ref = int(raw) if raw.lstrip("-").isascii() and raw.lstrip("-").isdigit() else raw
        chat = await bot.get_chat(chat_ref)
        if chat.type != ChatType.CHANNEL:
            raise ValueError("Faqat Telegram kanalini qo‘shish mumkin.")
        me = await bot.get_me()
        member = await bot.get_chat_member(chat.id, me.id)
        if member.status not in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
            raise ValueError("Bot kanalda admin emas. Avval botni kanalga admin qiling.")
        link = (
            f"https://t.me/{chat.username}"
            if chat.username
            else chat.invite_link or (await bot.create_chat_invite_link(chat.id)).invite_link
        )
    except (TelegramAPIError, ValueError) as exc:
        logging.warning("Kanal qo‘shish amalga oshmadi: %s", type(exc).__name__)
        if isinstance(exc, ValueError):
            reason = str(exc)
        elif isinstance(exc, TelegramForbiddenError):
            reason = "Bot kanalga kira olmayapti. Uni kanalga admin qilib qo‘shing."
        elif isinstance(exc, TelegramBadRequest):
            reason = "Kanal topilmadi yoki botning ruxsati yetarli emas. Kanal ID/username va taklif havolasi yaratish huquqini tekshiring."
        else:
            reason = "Telegram bilan aloqa vaqtincha ishlamayapti. Birozdan so‘ng qayta urinib ko‘ring."
        await message.answer(f"❌ {html.escape(reason)}\nQaytadan yuboring yoki bekor qiling.")
        return

    await db.add_channel(chat.id, chat.title, link)
    await state.clear()
    await message.answer(
        f"✅ <b>{html.escape(chat.title)}</b> majburiy kanallarga qo'shildi.",
        reply_markup=kb.admin_menu,
    )


@router.message(F.text == kb.BTN_CHANNELS)
async def list_channels(message: Message):
    channels = await db.get_channels()
    if not channels:
        await message.answer("Majburiy kanallar yo'q — foydalanuvchilar darhol ovoz bera oladi.")
        return
    await message.answer(
        "📢 Majburiy kanallar (o'chirish uchun bosing):",
        reply_markup=kb.admin_channels_kb(channels),
    )


@router.callback_query(kb.AdminChannelCB.filter())
async def delete_channel(call: CallbackQuery, callback_data: kb.AdminChannelCB):
    await db.delete_channel(callback_data.channel_id)
    channels = await db.get_channels()
    if channels:
        await call.message.edit_reply_markup(reply_markup=kb.admin_channels_kb(channels))
    else:
        await call.message.edit_text("Majburiy kanallar yo'q.")
    await call.answer("O'chirildi")


# ---------- statistika va xabar ----------

@router.message(F.text == kb.BTN_STATS)
async def stats(message: Message):
    total, voted = await db.stats()
    rows = await db.groups_rating()
    lines = [
        "📈 <b>Statistika</b>",
        f"Foydalanuvchilar: <b>{total}</b>",
        f"Ovoz berganlar: <b>{voted}</b>",
        "",
    ]
    lines += [f"{i}. {html.escape(g['name'])} — {g['votes']}" for i, g in enumerate(rows, 1)]
    await answer_lines(message, lines)


@router.message(F.text == kb.BTN_BROADCAST)
async def broadcast_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.broadcast)
    await message.answer(
        "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:",
        reply_markup=kb.cancel_kb,
    )


@router.message(AdminStates.broadcast)
async def broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⏳ Yuborilmoqda...", reply_markup=kb.admin_menu)
    sent = failed = 0
    for user_id in await db.all_user_ids():
        try:
            await message.copy_to(user_id)
            sent += 1
        except TelegramAPIError:
            failed += 1
        await asyncio.sleep(0.05)  # Telegram limitlaridan oshmaslik uchun
    await message.answer(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")


@router.message(AdminStates.group_name)
@router.message(AdminStates.channel)
async def require_text(message: Message):
    await message.answer("Iltimos, matn yuboring yoki ❌ Bekor qilish tugmasini bosing.")
