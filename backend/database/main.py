import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class Voicemail(BaseModel):
    id: int
    number: str
    name: str
    description: str
    spam: bool
    date: datetime
    unread: bool
    recording: Optional[str] = None

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
    return {"voicemails": memory_db["voicemails"]}

@app.post("/voicemails", response_model=Voicemail)
def post_voicemail(voicemail: Voicemail):
    memory_db["voicemails"].append(voicemail)
    return voicemail

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
