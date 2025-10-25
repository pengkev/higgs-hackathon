
from dotenv import load_dotenv
import os
from db_actions import init_db, add_row, read_table, Voicemail
from datetime import datetime



if __name__ == "__main__":
    load_dotenv()
    sqlite_url = os.getenv("SQLITECLOUD_URL")
    init_db(sqlite_url)
    vc_add=Voicemail(
        id="1",
        number="+1234567890",
        name="John Doe",
        description="Test voicemail",
        spam=False,
        date=datetime.utcnow(),
        unread=True
    )
    add_row(sqlite_url, vc_add)
    print(read_table(sqlite_url))
    
