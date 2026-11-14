"""SQLite setup. Tables follow the architecture: every fact keeps source and date."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id          TEXT PRIMARY KEY,
    area        TEXT NOT NULL,
    radius_km   INTEGER NOT NULL,
    product     TEXT NOT NULL,
    category    TEXT NOT NULL,
    exclusions  TEXT NOT NULL DEFAULT '[]',
    lat         REAL,
    lng         REAL,
    status      TEXT NOT NULL DEFAULT 'created',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id     TEXT NOT NULL REFERENCES searches(id),
    source        TEXT NOT NULL,
    source_id     TEXT,
    name          TEXT,
    address       TEXT,
    phone         TEXT,
    website       TEXT,
    lat           REAL,
    lng           REAL,
    source_url    TEXT,
    retrieved_at  TEXT NOT NULL,
    raw_json      TEXT
);

CREATE TABLE IF NOT EXISTS businesses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id           TEXT NOT NULL REFERENCES searches(id),
    name                TEXT NOT NULL,
    category            TEXT,
    address             TEXT,
    phone               TEXT,
    email               TEXT,
    website             TEXT,
    lat                 REAL,
    lng                 REAL,
    distance_km         REAL,
    status              TEXT,
    score               INTEGER,
    reason              TEXT,
    possible_duplicate  INTEGER NOT NULL DEFAULT 0,
    sources_json        TEXT NOT NULL DEFAULT '[]',
    last_verified       TEXT,
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id   INTEGER NOT NULL REFERENCES businesses(id),
    fact          TEXT NOT NULL,
    value         TEXT NOT NULL,
    source        TEXT NOT NULL,
    source_url    TEXT,
    retrieved_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id  INTEGER NOT NULL REFERENCES businesses(id),
    old_status   TEXT,
    new_status   TEXT NOT NULL,
    rule         TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_search ON raw_records(search_id);
CREATE INDEX IF NOT EXISTS idx_biz_search ON businesses(search_id);
CREATE INDEX IF NOT EXISTS idx_evidence_biz ON evidence(business_id);
"""


def utc_now() -> str:
    """Current time in UTC as text. Used for every retrieved_at / created_at."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_conn():
    """Open the database, save on success, undo on error, always close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they do not exist. Safe to run many times."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def save_raw_records(search_id: str, records: list[dict]) -> int:
    """Save connector output (Google / OSM). Returns how many rows were saved."""
    rows = [
        (
            search_id, r["source"], r.get("source_id"), r.get("name"), r.get("address"),
            r.get("phone"), r.get("website"), r.get("lat"), r.get("lng"),
            r.get("source_url"), r.get("retrieved_at") or utc_now(), r.get("raw_json"),
        )
        for r in records
    ]
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO raw_records
               (search_id, source, source_id, name, address, phone, website,
                lat, lng, source_url, retrieved_at, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
    return len(rows)


def save_search(search_id: str, data: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO searches (id, area, radius_km, product, category, exclusions, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (search_id, data["area"], data["radius_km"], data["product"], data["category"],
             json.dumps(data.get("exclusions", [])), utc_now()),
        )


def get_search(search_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM searches WHERE id = ?", (search_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["exclusions"] = json.loads(result["exclusions"])
    return result


def set_search_location(search_id: str, lat: float, lng: float) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE searches SET lat = ?, lng = ? WHERE id = ?", (lat, lng, search_id))


def set_search_status(search_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE searches SET status = ? WHERE id = ?", (status, search_id))


def save_business(search_id: str, lead: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO businesses
               (search_id, name, category, address, phone, email, website, lat, lng,
                distance_km, status, score, reason, possible_duplicate, sources_json,
                last_verified, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (search_id, lead["name"], lead.get("category"), lead.get("address"),
             lead.get("phone"), lead.get("email"), lead.get("website"),
             lead.get("lat"), lead.get("lng"), lead.get("distance_km"),
             lead.get("status"), lead.get("score"), lead.get("reason"),
             1 if lead.get("possible_duplicate") else 0,
             json.dumps(lead.get("sources", [])), lead.get("last_verified"), utc_now()),
        )
        return cur.lastrowid


def save_evidence(business_id: int, rows: list[tuple]) -> None:
    """rows = [(fact, value, source, source_url, retrieved_at), ...]"""
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO evidence (business_id, fact, value, source, source_url, retrieved_at)
               VALUES (?,?,?,?,?,?)""",
            [(business_id, *row) for row in rows],
        )


def save_verification_event(business_id: int, old_status: str | None, new_status: str, rule: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO verification_events (business_id, old_status, new_status, rule, created_at)
               VALUES (?,?,?,?,?)""",
            (business_id, old_status, new_status, rule, utc_now()),
        )


def maps_url_of(sources: list[dict]) -> str | None:
    """Exact Google Maps place link, if a Google record gave one."""
    for s in sources:
        if s.get("name") == "google" and s.get("url"):
            return s["url"]
    return None


def load_leads(search_id: str) -> list[dict]:
    """Read the final leads of one search. DB text columns become Python lists."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM businesses WHERE search_id = ? ORDER BY id", (search_id,)
        ).fetchall()
    leads = []
    for r in rows:
        lead = dict(r)
        lead["sources"] = json.loads(lead.get("sources_json") or "[]")
        lead["maps_url"] = maps_url_of(lead["sources"])
        leads.append(lead)
    return leads


def list_searches(limit: int = 50) -> list[dict]:
    """Past searches, newest first, with how many leads each one saved."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT s.id, s.area, s.radius_km, s.product, s.category,
                      s.status, s.created_at, COUNT(b.id) AS lead_count
               FROM searches s
               LEFT JOIN businesses b ON b.search_id = s.id
               GROUP BY s.id
               ORDER BY s.created_at DESC, s.rowid DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    with get_conn() as conn:
        tables = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    print("DB ready at:", DB_PATH)
    print("Tables:", ", ".join(tables))