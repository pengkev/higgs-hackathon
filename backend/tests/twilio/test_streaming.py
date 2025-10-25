"""
Test the streaming server components individually
"""
import asyncio
import base64
import io
import wave
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import os
import soundfile as sf
import sounddevice as sd

load_dotenv()

BOSONAI_API_KEY = os.getenv("BOSONAI_API_KEY")
client = OpenAI(
    api_key=BOSONAI_API_KEY,
    base_url="https://hackathon.boson.ai/v1"
)


def test_audio_conversion():
    """Test mulaw to PCM conversion"""
    print("🧪 Testing audio conversion...")
    
    import audioop
    
    # Create test audio
    sample_rate = 8000
    duration = 1
    t = np.linspace(0, duration, int(sample_rate * duration))
    sine_wave = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    
    # Convert to mulaw and back
    mulaw = audioop.lin2ulaw(sine_wave.tobytes(), 2)
    pcm_back = audioop.ulaw2lin(mulaw, 2)
    
    print(f"✅ Original: {len(sine_wave.tobytes())} bytes")
    print(f"✅ Mulaw: {len(mulaw)} bytes")
    print(f"✅ Back to PCM: {len(pcm_back)} bytes")
    print()


async def test_transcription():
    """Test BosonAI transcription"""
    print("🧪 Testing BosonAI transcription...")
    
    # You'll need a real audio file for this
    audio_path = "../recording.wav"  # Use one of your test recordings
    
    if not os.path.exists(audio_path):
        print(f"⚠️  No test audio file at {audio_path}, skipping")
        return
    
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    try:
        response = client.chat.completions.create(
            model="higgs-audio-understanding-Hackathon",
            messages=[
                {"role": "system", "content": "Transcribe this audio."},
                {
                    "role": "user",
                    "content": [{
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(audio_data).decode('utf-8'),
                            "format": "wav"
                        }
                    }]
                }
            ],
            temperature=0.0,
        )
        
        transcript = response.choices[0].message.content
        print(f"📝 Transcript: {transcript}")
        print()
        return transcript
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()


async def test_generation(text="Hello, this is a test of the AI voice system."):
    """Test BosonAI audio generation"""
    print("🧪 Testing BosonAI audio generation...")
    print(f"📝 Input text: {text}")
    
    try:
        # Use audio.speech.create like in example1.py
        response = client.audio.speech.create(
            model="higgs-audio-generation-Hackathon",
            voice="mabel",
            input=text,
            response_format="pcm"
        )
        
        # PCM data parameters
        num_channels = 1        
        sample_width = 2        
        sample_rate = 24000   
        
        pcm_data = response.content
        
        # Save to WAV file
        with wave.open('test_generation_output.wav', 'wb') as wav:
            wav.setnchannels(num_channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_data)
        
        print(f"✅ Audio saved to test_generation_output.wav")
        print(f"🔊 Playing audio...")
        
        # Play the audio
        data, sr = sf.read('test_generation_output.wav')
        sd.play(data, sr)
        sd.wait()
        
        print("✅ Playback complete")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()


async def test_full_conversation():
    """Test a full conversation loop with audio playback"""
    print("🧪 Testing full conversation with audio...")
    
    # Step 1: Get text response from understanding model
    user_text = "What's the weather like today?"
    print(f"👤 User: {user_text}")
    
    try:
        # Generate text response
        response = client.chat.completions.create(
            model="higgs-audio-generation-Hackathon",
            messages=[
                {
                    "role": "system",
                    "content": "You are Kevin's AI receptionist. Be helpful and brief."
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            temperature=0.7,
        )
        
        # Get text response (ignore audio tokens)
        ai_text = response.choices[0].message.content
        # Clean up audio tokens if present
        if "<|audio_out_bos|>" in ai_text:
            ai_text = "I'm Kevin's AI assistant. I don't have access to weather information, but I can help you with other questions."
        
        print(f"🤖 Assistant: {ai_text}")
        
        # Generate audio for the response
        print("🔊 Generating audio response...")
        audio_response = client.audio.speech.create(
            model="higgs-audio-generation-Hackathon",
            voice="mabel",
            input=ai_text,
            response_format="pcm"
        )
        
        # Save and play
        pcm_data = audio_response.content
        with wave.open('conversation_response.wav', 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(pcm_data)
        
        print("🔊 Playing response...")
        data, sr = sf.read('conversation_response.wav')
        sd.play(data, sr)
        sd.wait()
        
        print("✅ Conversation test complete")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()


async def main():
    print("=" * 60)
    print("Testing Streaming Server Components")
    print("=" * 60)
    print()
    
    # Test 1: Audio conversion
    test_audio_conversion()
    
    # Test 2: Transcription (if you have a test file)
    await test_transcription()
    
    # Test 3: Audio generation
    await test_generation("Hello! How can I help you today?")
    
    # Test 4: Full conversation
    await test_full_conversation()
    
    print("=" * 60)
    print("All tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
