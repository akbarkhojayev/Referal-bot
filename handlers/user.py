import html

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
from utils import not_subscribed_channels, ref_link, revoke_vote, user_mention

router = Router()


def parse_payload(payload: str | None, user_id: int):
    """start payload: r<user_id> — referal, g<group_id> — guruh linki."""
    referrer_id = group_id = None
    if payload and payload[1:].isdigit():
        if payload[0] == "r" and int(payload[1:]) != user_id:
            referrer_id = int(payload[1:])
        elif payload[0] == "g":
            group_id = int(payload[1:])
    return referrer_id, group_id


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot):
    user = message.from_user
    existing = await db.get_user(user.id)

    if existing is None:
        referrer_id, group_id = parse_payload(command.args, user.id)
        if referrer_id and not await db.get_user(referrer_id):
            referrer_id = None
        if group_id and not await db.get_group(group_id):
            group_id = None
        await db.add_user(user.id, user.full_name, user.username, referrer_id, group_id)
    else:
        await db.update_user_info(user.id, user.full_name, user.username)

    await message.answer(
        f"Assalomu alaykum, <b>{html.escape(user.full_name)}</b>!\n"
        "Bu bot orqali o'zingiz yoqtirgan guruhga ovoz berishingiz va "
        "do'stlaringizni taklif qilib ovoz yig'ishingiz mumkin."
    )
    await proceed(message, bot, user.id)


async def proceed(message: Message, bot: Bot, user_id: int):
    """Shartlar -> ovoz berish -> asosiy menyu."""
    missing = await not_subscribed_channels(bot, user_id)
    user = await db.get_user(user_id)

    if user["voted"]:
        if not missing:
            await show_main(message, bot, user_id)
            return
        # Bot o'chiq paytda kanaldan chiqqan bo'lsa ham ovoz -1 bo'ladi
        await revoke_vote(bot, user_id)
        user = await db.get_user(user_id)

    if missing:
        await message.answer(
            "Ovoz berish uchun quyidagi kanallarga a'zo bo'ling, so'ng "
            "<b>✅ Tekshirish</b> tugmasini bosing:",
            reply_markup=kb.subscribe_kb(missing),
        )
        return

    # Qaysi guruhga ovoz ketishini aniqlash: guruh linki yoki taklif qilgan odamning guruhi
    target_group = None
    if user["pending_group_id"]:
        target_group = await db.get_group(user["pending_group_id"])
    elif user["referrer_id"]:
        referrer = await db.get_user(user["referrer_id"])
        if referrer and referrer["voted"] and referrer["group_id"]:
            target_group = await db.get_group(referrer["group_id"])

    if target_group:
        await cast_vote(message, bot, user_id, target_group)
        return

    groups = await db.get_groups()
    if not groups:
        await message.answer("Hozircha guruhlar yo'q. Keyinroq urinib ko'ring.")
        return
    await message.answer(
        "Qaysi guruhga ovoz berasiz?", reply_markup=kb.groups_vote_kb(groups)
    )


async def cast_vote(message: Message, bot: Bot, user_id: int, group):
    if not await db.set_vote(user_id, group["id"]):
        await show_main(message, bot, user_id)
        return

    await message.answer(
        f"✅ Ovozingiz <b>{html.escape(group['name'])}</b> guruhiga qabul qilindi!"
    )

    user = await db.get_user(user_id)
    if user["referrer_id"]:
        refs = await db.referral_count(user["referrer_id"])
        try:
            await bot.send_message(
                user["referrer_id"],
                f"🎉 Sizning linkingiz orqali {user_mention(user)} ovoz berdi!\n"
                f"Jami taklif qilganlaringiz: <b>{refs}</b>",
            )
        except Exception:
            pass

    await show_main(message, bot, user_id)


async def show_main(message: Message, bot: Bot, user_id: int):
    user = await db.get_user(user_id)
    group = await db.get_group(user["group_id"])
    link = await ref_link(bot, user_id)
    await message.answer(
        f"Siz <b>{html.escape(group['name'])}</b> guruhi tarafdorisiz.\n\n"
        "Guruhingizga ko'proq ovoz yig'ish uchun quyidagi linkni do'stlaringizga "
        f"yuboring:\n{link}",
        reply_markup=kb.user_menu,
    )


@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery, bot: Bot):
    if await not_subscribed_channels(bot, call.from_user.id):
        await call.answer("❗ Siz hali barcha kanallarga a'zo bo'lmadingiz", show_alert=True)
        return
    await call.message.delete()
    await proceed(call.message, bot, call.from_user.id)


@router.callback_query(kb.VoteCB.filter())
async def vote(call: CallbackQuery, callback_data: kb.VoteCB, bot: Bot):
    user = await db.get_user(call.from_user.id)
    if user is None:
        await call.answer("Avval /start bosing", show_alert=True)
        return
    if user["voted"]:
        await call.answer("Siz allaqachon ovoz bergansiz", show_alert=True)
        return

    missing = await not_subscribed_channels(bot, call.from_user.id)
    if missing:
        await call.message.edit_text(
            "Avval kanallarga a'zo bo'ling:", reply_markup=kb.subscribe_kb(missing)
        )
        return

    group = await db.get_group(callback_data.group_id)
    if group is None:
        await call.answer("Bu guruh o'chirilgan", show_alert=True)
        return

    await call.message.delete()
    await cast_vote(call.message, bot, call.from_user.id, group)


@router.message(F.text == kb.BTN_MY_LINK)
async def my_link(message: Message, bot: Bot):
    user = await db.get_user(message.from_user.id)
    if not user or not user["voted"] or await not_subscribed_channels(bot, user["id"]):
        await proceed(message, bot, message.from_user.id)
        return
    link = await ref_link(bot, message.from_user.id)
    refs = await db.referral_count(message.from_user.id)
    await message.answer(
        f"🔗 Sizning referal linkingiz:\n{link}\n\n"
        f"Taklif qilganlaringiz: <b>{refs}</b>"
    )


@router.message(F.text == kb.BTN_RATING)
async def rating(message: Message):
    rows = await db.groups_rating()
    if not rows:
        await message.answer("Hozircha guruhlar yo'q.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["📊 <b>Guruhlar reytingi</b>\n"]
    for i, g in enumerate(rows):
        place = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{place} {html.escape(g['name'])} — <b>{g['votes']}</b> ovoz")
    await message.answer("\n".join(lines))


@router.message(F.text == kb.BTN_PROFILE)
async def profile(message: Message, bot: Bot):
    user = await db.get_user(message.from_user.id)
    if not user or not user["voted"] or await not_subscribed_channels(bot, user["id"]):
        await proceed(message, bot, message.from_user.id)
        return
    group = await db.get_group(user["group_id"])
    refs = await db.referral_count(user["id"])
    votes = await db.group_votes(user["group_id"])
    await message.answer(
        f"👤 <b>Profil</b>\n\n"
        f"Ism: {user_mention(user)}\n"
        f"Guruh: <b>{html.escape(group['name'])}</b> ({votes} ovoz)\n"
        f"Taklif qilganlaringiz: <b>{refs}</b>"
    )
