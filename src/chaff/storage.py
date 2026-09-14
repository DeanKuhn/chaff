"""Create database tables, save, update, and fetch data from them."""

import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime

from chaff.config import DB_PATH, ensure_dirs
from chaff.fingerprint import DeviceProfile

CONNECTION: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global CONNECTION
    if CONNECTION is None:
        ensure_dirs()
        CONNECTION = sqlite3.connect(DB_PATH)
        CONNECTION.execute("PRAGMA foreign_keys = ON")
    return CONNECTION


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS identities (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name      TEXT NOT NULL,
            last_name       TEXT NOT NULL,
            dob             TEXT NOT NULL,
            username        TEXT NOT NULL UNIQUE,
            backup_email    TEXT,
            locale          TEXT DEFAULT 'en_US',
            created_at      TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            identity_id     INTEGER NOT NULL,
            email           TEXT NOT NULL UNIQUE,
            password        TEXT NOT NULL,
            recovery_phone  TEXT,
            status          TEXT DEFAULT 'created',
            proxy_used      TEXT,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (identity_id) REFERENCES identities(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_profiles (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            identity_id         INTEGER NOT NULL,
            viewport_width      INTEGER NOT NULL,
            viewport_height     INTEGER NOT NULL,
            screen_width        INTEGER NOT NULL,
            screen_height       INTEGER NOT NULL,
            timezone_id         TEXT NOT NULL,
            locale              TEXT NOT NULL,
            user_agent          TEXT NOT NULL,
            color_depth         INTEGER NOT NULL,
            device_scale_factor INTEGER NOT NULL,
            platform            TEXT NOT NULL,
            FOREIGN KEY (identity_id) REFERENCES identities(id)
        )
    """)

    conn.commit()


def save_identity(
    first_name: str,
    last_name: str,
    dob: str,
    username: str,
    locale: str,
    backup_email: str | None = None,
) -> int | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO identities (
            first_name, 
            last_name, 
            dob, 
            username, 
            backup_email, 
            locale, 
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            first_name,
            last_name,
            dob,
            username,
            backup_email,
            locale,
            datetime.now(tz=UTC).isoformat(),
        ),
    )

    conn.commit()
    return cursor.lastrowid


def save_credential(
    identity_id: int | None,
    email: str,
    password: str,
    recovery_phone: str | None = None,
    proxy_used: str | None = None,
) -> int | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO credentials (
            identity_id, email, password, recovery_phone,
            proxy_used, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            identity_id,
            email,
            password,
            recovery_phone,
            proxy_used,
            datetime.now(tz=UTC).isoformat(),
        ),
    )

    conn.commit()
    return cursor.lastrowid


def save_profile(
    identity_id: int | None,
    profile: DeviceProfile | None,
) -> int | None:
    if not profile:
        return None
    d = asdict(profile)
    columns = ", ".join(d.keys())
    placeholders = ", ".join(["?"] * (len(d) + 1))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO device_profiles (identity_id, {columns}) VALUES ({placeholders})",
        (identity_id, *d.values()),
    )

    conn.commit()
    return cursor.lastrowid


def get_identities(status: str | None = None) -> list[sqlite3.Row]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if status is None:
        cursor.execute("""
            SELECT i.*, c.email, c.status, c.proxy_used
            FROM identities i
            LEFT JOIN credentials c
                ON c.identity_id = i.id
            ORDER BY i.created_at DESC
        """)
    else:
        cursor.execute(
            """
            SELECT i.*, c.email, c.status, c.proxy_used
            FROM identities i
            LEFT JOIN credentials c
                ON c.identity_id = i.id
            WHERE c.status = ?
            ORDER BY i.created_at DESC
        """,
            (status,),
        )

    return cursor.fetchall()


def update_status(status: str, credential_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE credentials SET status = ? WHERE id = ?
    """,
        (status, credential_id),
    )

    conn.commit()


def get_credential_by_email(email) -> list[sqlite3.Row]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT email, password, status, id, identity_id, proxy_used
        FROM credentials
        WHERE email = ?
    """,
        (email,),
    )
    return cursor.fetchall()


def get_credentials_by_status(status) -> list[sqlite3.Row]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT email, password, status, id, identity_id, proxy_used
        FROM credentials
        WHERE status = ?
    """,
        (status,),
    )
    return cursor.fetchall()


def get_profile(identity_id: int) -> DeviceProfile | None:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM device_profiles
        WHERE identity_id = ?
    """,
        (identity_id,),
    )
    row = cursor.fetchone()

    if not row:
        return None
    
    d = dict(row)
    del d["id"]
    del d["identity_id"]
    return DeviceProfile(**d)
