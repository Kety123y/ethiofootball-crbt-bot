import sqlite3
import json
import os
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name   TEXT NOT NULL,
            song_title  TEXT NOT NULL,
            crbt_code   TEXT NOT NULL UNIQUE,
            sms_command TEXT NOT NULL,
            preview_file TEXT NOT NULL,
            category    TEXT NOT NULL,
            league      TEXT NOT NULL DEFAULT 'Other'
        )
    """)
    conn.commit()
    conn.close()
    _seed_from_json()


def _seed_from_json():
    json_path = os.path.join("data", "songs.json")
    if not os.path.exists(json_path):
        return
    conn = get_connection()
    c = conn.cursor()
    with open(json_path, "r", encoding="utf-8") as f:
        songs = json.load(f)
    for s in songs:
        c.execute("""
            INSERT OR IGNORE INTO songs
                (team_name, song_title, crbt_code, sms_command, preview_file, category, league)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            s["team_name"], s["song_title"], s["crbt_code"],
            s["sms_command"], s["preview_file"], s["category"], s["league"]
        ))
    conn.commit()
    conn.close()


# ── Queries ──────────────────────────────────────────────────────────────────

def get_leagues():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT league FROM songs ORDER BY league").fetchall()
    conn.close()
    return [r["league"] for r in rows]


def get_teams_by_league(league: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT team_name FROM songs WHERE league=? ORDER BY team_name", (league,)
    ).fetchall()
    conn.close()
    return [r["team_name"] for r in rows]


def get_songs_by_team(team_name: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM songs WHERE team_name=? ORDER BY song_title", (team_name,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_song_by_id(song_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM songs WHERE id=?", (song_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def search_songs(query: str):
    like = f"%{query}%"
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM songs WHERE team_name LIKE ? OR song_title LIKE ? ORDER BY team_name",
        (like, like)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trending_songs(limit: int = 6):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM songs ORDER BY RANDOM() LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_songs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM songs ORDER BY team_name, song_title").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Admin CRUD ────────────────────────────────────────────────────────────────

def add_song(team_name, song_title, crbt_code, sms_command, preview_file, category, league):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO songs (team_name, song_title, crbt_code, sms_command, preview_file, category, league)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (team_name, song_title, crbt_code, sms_command, preview_file, category, league))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_song(song_id: int):
    conn = get_connection()
    c = conn.execute("DELETE FROM songs WHERE id=?", (song_id,))
    conn.commit()
    conn.close()
    return c.rowcount > 0
