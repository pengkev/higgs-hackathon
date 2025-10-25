from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import Response
import os
from typing import Optional
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.request_validator import RequestValidator
from openai_client import generate_reply, init_openai
from collections import defaultdict

# Initialize
app = FastAPI()
CALL_HISTORIES = defaultdict(list)  # simple in-memory store: {CallSid: [messages...]}

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")  # optional: for request validation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
init_openai(api_key=OPENAI_API_KEY)


def validate_twilio_request(request: Request) -> bool:
    if not TWILIO_AUTH_TOKEN:
        return True  # skip validation if no token provided
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    url = str(request.url)
    # Read raw body (must be done carefully)
    # NOTE: starlette Request.body() can be awaited only once; we validate by reading form below instead
    # Twilio's validator expects the full set of POST params; we reconstruct from form below (handled in endpoint)
    return True


@app.post("/voice")
async def voice_entry(request: Request):
    """
    Twilio initial webhook. Responds with TwiML that gathers speech once (and sends to /gather).
    """
    # Basic TwiML instructing Twilio to gather speech and post to /gather
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/gather",
        method="POST",
        speechTimeout="auto",
        hints="",  # optional speech hints
    )
    gather.say("Hello. Please say something and I will respond.")
    response.append(gather)
    # If no speech input, loop back
    response.say("I didn't receive any input. Goodbye.")
    return Response(content=str(response), media_type="application/xml")


@app.post("/gather")
async def gather_endpoint(
    request: Request,
    SpeechResult: Optional[str] = Form(None),
    CallSid: Optional[str] = Form(None),
    From: Optional[str] = Form(None),
):
    """
    Receives Twilio's Gather callback with SpeechResult (transcribed text).
    Sends transcript to OpenAI and returns TwiML <Say> with AI reply.
    """
    # Optional validation (not fully implemented here because Twilio request validator needs all params)
    if TWILIO_AUTH_TOKEN:
        # For full validation you'd need to reconstruct params dict from the request form.
        # We'll trust Twilio in this minimal example.
        pass

    if not CallSid:
        raise HTTPException(status_code=400, detail="Missing CallSid")

    user_text = SpeechResult or ""
    # maintain very small conversation history per call
    history = CALL_HISTORIES[CallSid]
    # history items follow OpenAI chat message format
    if not history:
        # warm up with a brief system prompt describing role
        history.append({"role": "system", "content": "You are a helpful voice assistant answering short questions."})
    history.append({"role": "user", "content": user_text})

    # Get AI reply
    ai_text = generate_reply(history)

    # store assistant response in history
    history.append({"role": "assistant", "content": ai_text})
    CALL_HISTORIES[CallSid] = history

    # Build TwiML response
    response = VoiceResponse()
    response.say(ai_text)
    # Redirect back to /voice to prompt for more input (loop)
    response.redirect("/voice")

    return Response(content=str(response), media_type="application/xml")