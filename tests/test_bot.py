import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import GetChatMember

import database as db
from handlers.channel import left_channel
from aiogram.filters import IS_NOT_MEMBER, ChatMemberUpdatedFilter
from handlers.user import parse_payload, proceed, vote
import keyboards as kb
from utils import SubscriptionCheckError, is_member, not_subscribed_channels


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = db.DB_PATH
        db.DB_PATH = str(Path(self.temp.name) / 'test.db')
        await db.init_db()
        self.group = await db.add_group('Sinov')
        await db.add_user(1, 'Ali', None)

    async def asyncTearDown(self):
        db.DB_PATH = self.original
        self.temp.cleanup()

    async def test_concurrent_vote_only_counts_once(self):
        results = await asyncio.gather(*(db.set_vote(1, self.group) for _ in range(10)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(await db.group_votes(self.group), 1)

    async def test_leave_restore_and_delete(self):
        await db.set_vote(1, self.group)
        self.assertTrue(await db.unvote(1))
        self.assertFalse(await db.unvote(1))
        self.assertEqual(await db.group_votes(self.group), 0)
        other = await db.add_group('Boshqa')
        self.assertFalse(await db.set_vote(1, other))
        self.assertTrue(await db.set_vote(1, self.group))
        await db.delete_group(self.group)
        user = await db.get_user(1)
        self.assertFalse(user['voted'])
        self.assertIsNone(user['group_id'])
        self.assertFalse(await db.set_vote(1, self.group))
        self.assertTrue(await db.set_vote(1, other))

    async def test_channel_leave_removes_vote_and_referral_once(self):
        await db.add_user(2, 'Vali', None, referrer_id=1)
        await db.set_vote(1, self.group)
        await db.set_vote(2, self.group)
        await db.add_channel(-1001, 'Majburiy kanal', 'https://t.me/example')
        event = SimpleNamespace(
            chat=SimpleNamespace(id=-1001),
            new_chat_member=SimpleNamespace(user=SimpleNamespace(id=2)),
        )
        bot = SimpleNamespace(send_message=AsyncMock())
        await left_channel(event, bot)
        self.assertEqual(await db.group_votes(self.group), 1)
        self.assertEqual(await db.referral_count(1), 0)
        self.assertEqual((await db.get_user(2))['pending_group_id'], self.group)
        self.assertEqual(bot.send_message.await_count, 2)
        self.assertIn('(-1)', bot.send_message.call_args_list[0].args[1])
        await left_channel(event, bot)
        self.assertEqual(await db.group_votes(self.group), 1)
        self.assertEqual(bot.send_message.await_count, 2)

    async def test_unconfigured_channel_does_not_remove_vote(self):
        await db.set_vote(1, self.group)
        event = SimpleNamespace(chat=SimpleNamespace(id=-999), new_chat_member=SimpleNamespace(user=SimpleNamespace(id=1)))
        bot = SimpleNamespace(send_message=AsyncMock())
        await left_channel(event, bot)
        self.assertEqual(await db.group_votes(self.group), 1)
        bot.send_message.assert_not_awaited()

    async def test_nonmember_events_are_detected(self):
        check = ChatMemberUpdatedFilter(IS_NOT_MEMBER)
        for status, member in [('left', False), ('kicked', False), ('restricted', False)]:
            event = SimpleNamespace(old_chat_member=SimpleNamespace(status='member'), new_chat_member=SimpleNamespace(status=status, is_member=member))
            self.assertTrue(await check(event))
        event.new_chat_member = SimpleNamespace(status='member')
        self.assertFalse(await check(event))

    async def test_channel_upsert_keeps_id(self):
        await db.add_channel(-1001, 'Kanal', 'https://t.me/example')
        first = (await db.get_channels())[0]['id']
        await db.add_channel(-1001, 'Yangi', 'https://t.me/example2')
        channels = await db.get_channels()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]['id'], first)

    async def test_network_failure_keeps_vote(self):
        await db.set_vote(1, self.group)
        await db.add_channel(-1001, 'Kanal', 'https://t.me/example')
        bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=TelegramNetworkError(
            method=GetChatMember(chat_id=-1001, user_id=1), message='test'
        )))
        with self.assertRaises(SubscriptionCheckError):
            await not_subscribed_channels(bot, 1)
        self.assertEqual(await db.group_votes(self.group), 1)

    async def test_menu_before_start(self):
        message = SimpleNamespace(answer=AsyncMock())
        await proceed(message, None, 999)
        self.assertIn('/start', message.answer.call_args.args[0])

    async def test_stale_vote_button_preserves_referral_target(self):
        await db.set_vote(1, self.group)
        await db.add_user(2, 'Vali', None, referrer_id=1)
        other = await db.add_group('Boshqa')
        call = SimpleNamespace(from_user=SimpleNamespace(id=2), answer=AsyncMock(), message=object())
        with patch('handlers.user.not_subscribed_channels', AsyncMock(return_value=[])), patch('handlers.user.proceed', AsyncMock()) as next_step:
            await vote(call, kb.VoteCB(group_id=other), None)
            next_step.assert_awaited_once()
        self.assertFalse((await db.get_user(2))['voted'])


class PayloadTests(unittest.TestCase):
    def test_invalid_payloads(self):
        for value in [None, '', 'r', 'r0', 'r1', 'g-1', 'r' + '9' * 80, 'g²', 'g١']:
            self.assertEqual(parse_payload(value, 1), (None, None))
        self.assertEqual(parse_payload('r2', 1), (2, None))
        self.assertEqual(parse_payload('g3', 1), (None, 3))

    def test_restricted_membership(self):
        self.assertFalse(is_member(SimpleNamespace(status=ChatMemberStatus.RESTRICTED, is_member=False)))
        self.assertTrue(is_member(SimpleNamespace(status=ChatMemberStatus.RESTRICTED, is_member=True)))


if __name__ == '__main__':
    unittest.main()
