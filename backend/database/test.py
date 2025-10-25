from dotenv import load_dotenv
import os
from db_actions import (
    init_db,
    add_row,
    read_table,
    Voicemail,
    delete_table,
    delete_rows,
    get_recording,
    add_object_row
)
from datetime import datetime, timezone
from voicemail import voicemails



if __name__ == "__main__":

    # Example usage:
    # file_name = "../recordings/call1.wav"
    # wav_bytes = wav_to_bytes(file_name)

    load_dotenv()
    sqlite_url = os.getenv("SQLITECLOUD_URL")

    #delete_table(sqlite_url)
    init_db(sqlite_url)
    # # vc_add = Voicemail(
    # #     id="1",
    # #     number="+1234567890",
    # #     name="John Doe",
    # #     description="Test voicemail",
    # #     spam=False,
    # #     date=datetime.now(timezone.utc),
    # #     unread=True,
    # #     recording="call1.wav",
    # # )
    #add_object_row(sqlite_url, voicemails)
    print(read_table(sqlite_url))
    get_recording(sqlite_url, 3)
    # add_row(sqlite_url, vc_add)
    # print(read_table(sqlite_url)[2].recording)
    # bytes_to_wav(read_table(sqlite_url)[2].recording, 'output.wav', 1, 2, 8000)
