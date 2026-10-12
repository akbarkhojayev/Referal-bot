from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config import INSTAGRAM_URL


class VoteCB(CallbackData, prefix="vote"):
    group_id: int


class AdminGroupCB(CallbackData, prefix="agroup"):
    action: str  # view | delete
    group_id: int


class AdminChannelCB(CallbackData, prefix="achan"):
    channel_id: int


# ---------- user ----------

BTN_MY_LINK = "🔗 Mening linkim"
BTN_RATING = "📊 Reyting"
BTN_PROFILE = "👤 Profil"

user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_MY_LINK)],
        [KeyboardButton(text=BTN_RATING), KeyboardButton(text=BTN_PROFILE)],
    ],
    resize_keyboard=True,
)


def subscribe_kb(channels):
    rows = [[InlineKeyboardButton(text=f"➕ {ch['title']}", url=ch["link"])] for ch in channels]
    if channels:
        rows.append([InlineKeyboardButton(text="📸 Instagram", url=INSTAGRAM_URL)])
    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def groups_vote_kb(groups):
    rows = [
        [InlineKeyboardButton(text=g["name"], callback_data=VoteCB(group_id=g["id"]).pack())]
        for g in groups
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- admin ----------

BTN_ADD_GROUP = "➕ Guruh qo'shish"
BTN_GROUPS = "📋 Guruhlar"
BTN_CHANNELS = "📢 Kanallar (shartlar)"
BTN_ADD_CHANNEL = "➕ Kanal qo'shish"
BTN_STATS = "📈 Statistika"
BTN_BROADCAST = "✉️ Xabar yuborish"
BTN_CANCEL = "❌ Bekor qilish"

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_ADD_GROUP), KeyboardButton(text=BTN_GROUPS)],
        [KeyboardButton(text=BTN_ADD_CHANNEL), KeyboardButton(text=BTN_CHANNELS)],
        [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_BROADCAST)],
    ],
    resize_keyboard=True,
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
    resize_keyboard=True,
)


def admin_groups_kb(groups):
    rows = [
        [InlineKeyboardButton(
            text=f"{g['name']} — {g['votes']} ovoz",
            callback_data=AdminGroupCB(action="view", group_id=g["id"]).pack(),
        )]
        for g in groups
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_group_detail_kb(group_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🗑 O'chirish",
            callback_data=AdminGroupCB(action="delete", group_id=group_id).pack(),
        )
    ]])


def admin_channels_kb(channels):
    rows = [
        [InlineKeyboardButton(
            text=f"🗑 {ch['title']}",
            callback_data=AdminChannelCB(channel_id=ch["id"]).pack(),
        )]
        for ch in channels
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
