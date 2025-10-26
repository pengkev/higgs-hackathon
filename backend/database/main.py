import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from dataclasses import asdict
from db_actions import Voicemail, read_table, get_recording, edit_row_unread
from dotenv import load_dotenv
import os

# class Voicemail(BaseModel):
#     id: int
#     number: str
#     name: str
#     description: str
#     spam: bool
#     date: datetime
#     unread: bool
#     recording: Optional[str] = None


class VoicemailList(BaseModel):
    voicemails: List[Voicemail]


app = FastAPI()

origins = ["http://localhost:8081"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_db = {"voicemails": []}


@app.get("/voicemails", response_model=VoicemailList)
def get_voicemails():
    load_dotenv()
    sqlite_url = os.getenv("SQLITECLOUD_URL")
    voicemails = read_table(sqlite_url)
    existing_ids = {vm.id for vm in memory_db["voicemails"]}

    for vm in voicemails:
        if vm.id not in existing_ids:
            memory_db["voicemails"].append(vm)
    return {"voicemails": memory_db["voicemails"]}


@app.put("/voicemails")
def put_recording(voicemail: Voicemail):
    load_dotenv()
    sqlite_url = os.getenv("SQLITECLOUD_URL")
    for i, vm in enumerate(memory_db["voicemails"]):
        if vm.id == voicemail.id:
            # update the object in memory
            edit_row_unread(sqlite_url, voicemail)
            memory_db["voicemails"][i].unread = voicemail.unread
            
            blob = get_recording(sqlite_url, voicemail.id)
            return Response(content=blob, media_type="audio/wav")

if __name__ == "__main__":
    get_voicemails()
    uvicorn.run(app, host="0.0.0.0", port=8000)
