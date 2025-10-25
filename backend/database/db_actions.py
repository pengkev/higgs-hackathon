import sqlitecloud
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from wav_bytes import wav_to_bytes, bytes_to_wav


@dataclass
class Voicemail:
    id: int
    number: str
    name: str
    description: str
    spam: bool
    date: datetime
    unread: bool
    recording: str | None


def get_conn(sqlite_url) -> sqlitecloud.Connection:
    """
    Opens a connection to the voicemails.sqlite database.
    """
    return sqlitecloud.connect(sqlite_url)


def init_db(sqlite_url) -> None:
    """
    Creates the voicemails table if it does not exist.
    """
    conn = get_conn(sqlite_url)
    try:
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS voicemails (
            id INTEGER PRIMARY KEY,
            number TEXT NOT NULL,
            name TEXT,
            description TEXT,
            spam INTEGER NOT NULL DEFAULT 0,
            date TEXT NOT NULL,          
            unread INTEGER NOT NULL DEFAULT 1,
            recording BLOB NOT NULL DEFAULT ''
        );
        """
        )
        conn.commit()
    finally:
        conn.close()


def add_row(sqlite_url, voicemail: Voicemail) -> None:
    """
    Adds a sample row to the voicemails table.
    """
    conn = get_conn(sqlite_url)
    recording = wav_to_bytes(f"../recordings/{voicemail.recording}")
    try:
        id = conn.execute("SELECT COUNT(*) FROM voicemails;").fetchone()[0] + 1
        conn.execute(
            """
        INSERT INTO voicemails (id, number, name, description, spam, date, unread, recording)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
            (
                id,
                voicemail.number,
                voicemail.name,
                voicemail.description,
                voicemail.spam == True and 1 or 0,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                1,
                recording,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def add_object_row(sqlite_url, voicemail: List[Voicemail]):
    """Adds all Voicemails in the list to the voicemails table."""
    for voice in voicemail:
        add_row(sqlite_url, voice)


def read_table(sqlite_url) -> List[Voicemail]:
    """
    Reads and returns all rows from the voicemails table.
    """
    conn = get_conn(sqlite_url)
    voicemails: List[Voicemail] = []
    try:
        cursor = conn.execute("SELECT * FROM voicemails;")
        rows = cursor.fetchall()
        for row in rows:
            vm = Voicemail(
                id=row[0],
                number=row[1],
                name=row[2],
                description=row[3],
                spam=bool(row[4]),
                date=datetime.fromisoformat(row[5].replace("Z", "+00:00")),
                unread=bool(row[6]),
                recording= f'{row[0]}.wav',
            )

            voicemails.append(vm)

    finally:
        conn.close()
    return voicemails


def get_recording(sqlite_url, voicemail_id: int) -> bytes | None:
    conn = get_conn(sqlite_url)
    try:
        cursor = conn.execute(
            "SELECT recording FROM voicemails WHERE id = ?;", (voicemail_id,)
        )
        row = cursor.fetchone()
        if row:
            return row[0]
            #bytes_to_wav(row[0], f'../output_recordings/{voicemail_id}.wav', 1, 2, 8000) 
    finally:
        conn.close()


def delete_rows(sqlite_url) -> None:
    """
    Deletes all rows from the voicemails table.
    """
    conn = get_conn(sqlite_url)
    try:
        conn.execute("DELETE FROM voicemails;")
        conn.commit()
    finally:
        conn.close()


def delete_table(sqlite_url) -> None:
    """
    Deletes all rows from the voicemails table.
    """
    conn = get_conn(sqlite_url)
    try:
        conn.execute("DROP TABLE IF EXISTS voicemails;")
        conn.commit()
    finally:
        conn.close()
