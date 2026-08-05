import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone

from . import config

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(config.DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def now_ts() -> int:
    return int(time.time())


def local_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=config.TZ_OFFSET)


def day_key() -> str:
    return local_now().strftime("%Y-%m-%d")


def week_key() -> str:
    iso = local_now().isocalendar()  # ISO hafta — dushanbadan boshlanadi
    return f"{iso.year}-W{iso.week:02d}"


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,              -- Telegram user id
    first_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    referred_by INTEGER,
    activated_at INTEGER,                -- obuna tekshiruvidan o'tgan vaqt
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL UNIQUE,        -- @username yoki -100... id
    title TEXT DEFAULT '',
    invite_link TEXT DEFAULT '',
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    options TEXT NOT NULL,               -- JSON massiv
    correct_idx INTEGER NOT NULL,
    time_limit INTEGER NOT NULL DEFAULT 30,
    active INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    day TEXT NOT NULL,
    week TEXT NOT NULL,
    questions TEXT NOT NULL,             -- JSON: [{qid, served_at, answer_idx, correct, points, elapsed}]
    current_idx INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    finished INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    UNIQUE(user_id, day)
);

CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',   -- draft | active | closed
    created_at INTEGER NOT NULL,
    started_at INTEGER,
    closed_at INTEGER
);

CREATE TABLE IF NOT EXISTS poll_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS poll_votes (
    poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    option_id INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    voted_at INTEGER NOT NULL,
    PRIMARY KEY (poll_id, user_id)
);

CREATE TABLE IF NOT EXISTS ref_winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_num INTEGER NOT NULL,          -- 1 yoki 2
    user_id INTEGER NOT NULL REFERENCES users(id),
    ref_count INTEGER NOT NULL,
    drawn_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "daily_question_count": "10",
    "default_time_limit": "30",
    "ref_group1_min": "4",   # 3 tadan ko'p
    "ref_group2_min": "6",   # 5 tadan ko'p
}


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
    conn.commit()


def get_setting(key: str, default: str = "") -> str:
    row = get_conn().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


# ---------- Foydalanuvchilar ----------

def upsert_user(uid: int, first_name: str, username: str, referred_by: int | None = None):
    conn = get_conn()
    row = conn.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
    if row is None:
        if referred_by == uid:
            referred_by = None
        conn.execute(
            "INSERT INTO users(id, first_name, username, referred_by, created_at) VALUES(?,?,?,?,?)",
            (uid, first_name or "", username or "", referred_by, now_ts()),
        )
    else:
        conn.execute(
            "UPDATE users SET first_name=?, username=? WHERE id=?",
            (first_name or "", username or "", uid),
        )
    conn.commit()


def activate_user(uid: int):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET activated_at=? WHERE id=? AND activated_at IS NULL",
        (now_ts(), uid),
    )
    conn.commit()


def get_user(uid: int):
    return get_conn().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def ref_count(uid: int) -> int:
    row = get_conn().execute(
        "SELECT COUNT(*) AS c FROM users WHERE referred_by=? AND activated_at IS NOT NULL",
        (uid,),
    ).fetchone()
    return row["c"]


def ref_leaderboard(limit: int = 50):
    return get_conn().execute(
        """
        SELECT u.id, u.first_name, u.username, COUNT(r.id) AS refs
        FROM users u
        JOIN users r ON r.referred_by = u.id AND r.activated_at IS NOT NULL
        GROUP BY u.id
        ORDER BY refs DESC, u.created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def ref_group_members(min_refs: int):
    return get_conn().execute(
        """
        SELECT u.id, u.first_name, u.username, COUNT(r.id) AS refs
        FROM users u
        JOIN users r ON r.referred_by = u.id AND r.activated_at IS NOT NULL
        GROUP BY u.id
        HAVING refs >= ?
        ORDER BY refs DESC
        """,
        (min_refs,),
    ).fetchall()


# ---------- Viktorina ----------

def quiz_leaderboard(week: str, limit: int = 50):
    return get_conn().execute(
        """
        SELECT u.id, u.first_name, u.username,
               SUM(s.score) AS score, SUM(s.correct_count) AS correct,
               COUNT(s.id) AS days_played
        FROM quiz_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.week = ? AND s.finished = 1
        GROUP BY u.id
        ORDER BY score DESC, correct DESC
        LIMIT ?
        """,
        (week, limit),
    ).fetchall()


def session_questions(row) -> list:
    return json.loads(row["questions"])


def save_session_questions(session_id: int, questions: list, current_idx: int,
                           score: int, correct_count: int, finished: bool):
    conn = get_conn()
    conn.execute(
        """UPDATE quiz_sessions
           SET questions=?, current_idx=?, score=?, correct_count=?, finished=?
           WHERE id=?""",
        (json.dumps(questions), current_idx, score, correct_count, int(finished), session_id),
    )
    conn.commit()
