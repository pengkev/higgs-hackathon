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

# Transcribe audio
audio_path = "input_audio.wav"
audio_base64 = encode_audio_to_base64(audio_path)
file_format = audio_path.split(".")[-1]

response = client.chat.completions.create(
    model="higgs-audio-understanding-Hackathon",
    messages=[
        {"role": "system", "content": "You are a helpful assistant. Please respond to the caller as if you were answering a call for your boss and avoiding spam or suspicious calls."},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_base64,
                        "format": file_format,
                    },
                },
            ],
        },
        {
            "role": "user",
            "content": "How would you, as an assistant receptionist for your boss, respond to this message for him?",
        },
    ],
    temperature=0.0,
)

modelresponse = response.choices[0].message.content

print(modelresponse)

response = client.audio.speech.create(
    model="higgs-audio-generation-Hackathon",
    voice="mabel",
    input=modelresponse,
    response_format="pcm"
)

# You can use these parameters to write PCM data to a WAV file
num_channels = 1        
sample_width = 2        
sample_rate = 24000   

pcm_data = response.content

with wave.open('output_audio.wav', 'wb') as wav:
    wav.setnchannels(num_channels)
    wav.setsampwidth(sample_width)
    wav.setframerate(sample_rate)
    wav.writeframes(pcm_data)