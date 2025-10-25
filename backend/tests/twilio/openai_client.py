import os
import openai
from typing import List, Dict

def init_openai(api_key: str = None):
    if api_key:
        openai.api_key = api_key
    else:
        # rely on OPENAI_API_KEY env var if provided
        openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_reply(messages: List[Dict], model: str = "gpt-3.5-turbo") -> str:
    """
    messages should be a list following the openai Chat API format:
    [{"role": "system","content":"..."}, {"role":"user","content":"..."} ...]
    """
    # Keep safe defaults
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )
        return resp.choices[0].message["content"].strip()
    except Exception as e:
        # fallback
        return "Sorry, I'm having trouble connecting to the AI service right now."