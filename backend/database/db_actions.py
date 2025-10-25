import sqlitecloud
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

@dataclass
class Voicemail:
    id: str
    number: str
    name: str
    description: str
    spam: bool
    date: datetime
    unread: bool


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
        conn.execute("""
        CREATE TABLE IF NOT EXISTS voicemails (
            id TEXT PRIMARY KEY,
            number TEXT NOT NULL,
            name TEXT,
            description TEXT,
            spam BOOLEAN NOT NULL DEFAULT 0,
            date TEXT NOT NULL,          
            unread BOOLEAN NOT NULL DEFAULT 1
        );
        """)
        conn.commit()
    finally:
        conn.close()
        
def add_row(sqlite_url, voicemail: Voicemail) -> None:
    """
    Adds a sample row to the voicemails table.
    """
    
    conn = get_conn(sqlite_url)
    
    try:
        id = conn.execute("SELECT COUNT(*) FROM voicemails;").fetchone()[0] + 1
        conn.execute("""
        INSERT INTO voicemails (id, number, name, description, spam, date, unread)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (id, voicemail.number, voicemail.name, voicemail.description, voicemail.spam, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), True))
        conn.commit()
    finally:
        conn.close()
        
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
                unread=bool(row[6])
            )
          
            voicemails.append(vm)
        
    finally:
        conn.close()
    return voicemails
    