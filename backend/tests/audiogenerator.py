import openai
import base64
import os
import wave
from dotenv import load_dotenv

load_dotenv()

BOSON_API_KEY = os.getenv("BOSONAI_API_KEY")

def encode_audio_to_base64(file_path: str) -> str:
    """Encode audio file to base64 format."""
    with open(file_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode("utf-8")

client = openai.Client(
    api_key=BOSON_API_KEY,
    base_url="https://hackathon.boson.ai/v1"
)


response = client.audio.speech.create(
    model="higgs-audio-generation-Hackathon",
    voice="vex",
    input="Hi, this is Mark calling from United Auto Warranty. I see that the Warranty on your Lexus has expired earlier this month and I was just calling to see if you would like to extend this warranty to keep your car protected for an additional 2 years.",
    response_format="pcm"
)

# You can use these parameters to write PCM data to a WAV file
num_channels = 1        
sample_width = 2        
sample_rate = 24000   

pcm_data = response.content

with wave.open('scammer.wav', 'wb') as wav:
    wav.setnchannels(num_channels)
    wav.setsampwidth(sample_width)
    wav.setframerate(sample_rate)
    wav.writeframes(pcm_data)