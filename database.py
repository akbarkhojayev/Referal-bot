import aiosqlite

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    referrer_id INTEGER,
    pending_group_id INTEGER,
    group_id INTEGER,
    voted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER UNIQUE NOT NULL,
    title TEXT,
    link TEXT
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def _fetchone(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return await cur.fetchone()


async def _fetchall(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return await cur.fetchall()


async def _execute(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.lastrowid


# ---------- users ----------

async def get_user(user_id):
    return await _fetchone("SELECT * FROM users WHERE id = ?", (user_id,))


async def add_user(user_id, full_name, username, referrer_id=None, pending_group_id=None):
    await _execute(
        "INSERT OR IGNORE INTO users (id, full_name, username, referrer_id, pending_group_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, full_name, username, referrer_id, pending_group_id),
    )


async def update_user_info(user_id, full_name, username):
    await _execute(
        "UPDATE users SET full_name = ?, username = ? WHERE id = ?",
        (full_name, username, user_id),
    )


async def set_vote(user_id, group_id):
    """Foydalanuvchi ovozini guruhga yozadi. Agar allaqachon ovoz bergan bo'lsa False."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE users SET group_id = ?, voted = 1, pending_group_id = NULL "
            "WHERE id = ? AND voted = 0",
            (group_id, user_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def all_user_ids():
    rows = await _fetchall("SELECT id FROM users")
    return [r["id"] for r in rows]


async def referral_count(user_id):
    row = await _fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE referrer_id = ? AND voted = 1", (user_id,)
    )
    return row["c"]


async def top_referrers(group_id, limit=10):
    return await _fetchall(
        """
        SELECT u.id, u.full_name, u.username, COUNT(r.id) AS refs
        FROM users u
        JOIN users r ON r.referrer_id = u.id AND r.voted = 1
        WHERE u.group_id = ?
        GROUP BY u.id
        ORDER BY refs DESC
        LIMIT ?
        """,
        (group_id, limit),
    )


async def stats():
    row = await _fetchone(
        "SELECT COUNT(*) AS total, COALESCE(SUM(voted), 0) AS voted FROM users"
    )
    return row["total"], row["voted"]


# ---------- groups ----------

async def add_group(name):
    return await _execute("INSERT INTO groups (name) VALUES (?)", (name,))


async def get_group(group_id):
    return await _fetchone("SELECT * FROM groups WHERE id = ?", (group_id,))


async def get_groups():
    return await _fetchall("SELECT * FROM groups ORDER BY id")


async def groups_rating():
    return await _fetchall(
        """
        SELECT g.id, g.name, COUNT(u.id) AS votes
        FROM groups g
        LEFT JOIN users u ON u.group_id = g.id AND u.voted = 1
        GROUP BY g.id
        ORDER BY votes DESC, g.id
        """
    )


async def group_votes(group_id):
    row = await _fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE group_id = ? AND voted = 1", (group_id,)
    )
    return row["c"]


async def delete_group(group_id):
    async with aiosqlite.connect(DB_PATH) as db:
        # Guruh o'chsa, uning ovozchilari qaytadan ovoz bera oladi
        await db.execute(
            "UPDATE users SET group_id = NULL, voted = 0 WHERE group_id = ?", (group_id,)
        )
        await db.execute(
            "UPDATE users SET pending_group_id = NULL WHERE pending_group_id = ?", (group_id,)
        )
        await db.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        await db.commit()


# ---------- channels (shartlar) ----------

async def add_channel(chat_id, title, link):
    await _execute(
        "INSERT OR REPLACE INTO channels (chat_id, title, link) VALUES (?, ?, ?)",
        (chat_id, title, link),
    )


async def get_channels():
    return await _fetchall("SELECT * FROM channels ORDER BY id")


async def delete_channel(channel_id):
    await _execute("DELETE FROM channels WHERE id = ?", (channel_id,))


async def unvote(user_id):
    """Kanaldan chiqqan foydalanuvchi ovozini olib tashlaydi.
    Guruh pending_group_id ga saqlanadi — qayta a'zo bo'lsa ovoz o'sha guruhga qaytadi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE users SET voted = 0, pending_group_id = group_id, group_id = NULL "
            "WHERE id = ? AND voted = 1",
            (user_id,),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_channel_by_chat(chat_id):
    return await _fetchone("SELECT * FROM channels WHERE chat_id = ?", (chat_id,))
