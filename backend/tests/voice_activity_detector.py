"""
Voice Activity Detection (VAD) - Records from microphone until silence is detected
Automatically stops recording at the end of a sentence/pause
"""
import sounddevice as sd
import soundfile as sf
import numpy as np
import wave
from collections import deque
import time

# Audio settings
SAMPLE_RATE = 16000  # 16kHz is good for speech
CHANNELS = 1
DTYPE = 'int16'

# VAD parameters
SILENCE_THRESHOLD = 500  # Amplitude threshold (adjust based on your mic)
SILENCE_DURATION = 1.5   # Seconds of silence to detect end of sentence
CHUNK_DURATION = 0.1     # Process audio in 100ms chunks

class VoiceActivityDetector:
    def __init__(self, 
                 sample_rate=SAMPLE_RATE,
                 silence_threshold=SILENCE_THRESHOLD,
                 silence_duration=SILENCE_DURATION,
                 chunk_duration=CHUNK_DURATION):
        
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        
        # Buffer to store audio chunks
        self.audio_buffer = []
        
        # Track silence duration
        self.silence_chunks = 0
        self.required_silence_chunks = int(silence_duration / chunk_duration)
        
        # Track if we've detected speech
        self.speech_detected = False
        self.is_recording = True
        
    def is_silence(self, audio_chunk):
        """Check if audio chunk is silence"""
        # Calculate RMS (Root Mean Square) amplitude
        rms = np.sqrt(np.mean(audio_chunk**2))
        return rms < self.silence_threshold
    
    def process_chunk(self, audio_chunk):
        """Process incoming audio chunk"""
        # Store the chunk
        self.audio_buffer.append(audio_chunk.copy())
        
        if self.is_silence(audio_chunk):
            # If we've detected speech before, count silence
            if self.speech_detected:
                self.silence_chunks += 1
                
                # Check if we've had enough silence
                if self.silence_chunks >= self.required_silence_chunks:
                    print("🛑 End of sentence detected!")
                    self.is_recording = False
                    return False
            # else: still waiting for speech to start
        else:
            # Speech detected
            if not self.speech_detected:
                print("🎤 Speech detected, recording...")
            self.speech_detected = True
            self.silence_chunks = 0
        
        return True
    
    def get_audio(self):
        """Get all recorded audio as numpy array"""
        if not self.audio_buffer:
            return np.array([], dtype=DTYPE)
        return np.concatenate(self.audio_buffer)
    
    def save_to_wav(self, filename):
        """Save recorded audio to WAV file"""
        audio_data = self.get_audio()
        
        if len(audio_data) == 0:
            print("⚠️  No audio recorded")
            return False
        
        # Save using wave module for more control
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        duration = len(audio_data) / self.sample_rate
        print(f"✅ Saved {duration:.2f} seconds to {filename}")
        return True


def record_until_silence(output_file="recording.wav", 
                         silence_threshold=SILENCE_THRESHOLD,
                         max_duration=30):
    """
    Record from microphone until silence is detected at end of sentence
    
    Args:
        output_file: Output WAV filename
        silence_threshold: Amplitude threshold for silence detection
        max_duration: Maximum recording duration in seconds (safety limit)
    """
    print("🎙️  Voice Activity Detection Ready")
    print(f"Silence threshold: {silence_threshold}")
    print(f"Will stop after {SILENCE_DURATION}s of silence")
    print("\nSpeak now... (recording will auto-stop when you finish)\n")
    
    vad = VoiceActivityDetector(silence_threshold=silence_threshold)
    
    chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
    max_chunks = int(max_duration / CHUNK_DURATION)
    chunk_count = 0
    
    def audio_callback(indata, frames, time_info, status):
        """Called for each audio chunk"""
        nonlocal chunk_count
        
        if status:
            print(f"Status: {status}")
        
        # Safety check - stop if max duration reached
        chunk_count += 1
        if chunk_count >= max_chunks:
            print(f"\n⏱️  Maximum duration ({max_duration}s) reached")
            raise sd.CallbackAbort
        
        # Process the chunk
        audio_chunk = indata[:, 0] if indata.ndim > 1 else indata
        
        if not vad.process_chunk(audio_chunk):
            # Silence detected, stop recording
            raise sd.CallbackStop
    
    try:
        # Start recording
        with sd.InputStream(
            channels=CHANNELS,
            samplerate=SAMPLE_RATE,
            dtype=DTYPE,
            blocksize=chunk_size,
            callback=audio_callback
        ):
            # Wait until recording stops
            while vad.is_recording:
                sd.sleep(100)
    
    except sd.CallbackStop:
        pass
    except sd.CallbackAbort:
        pass
    except KeyboardInterrupt:
        print("\n⚠️  Recording interrupted by user")
    
    # Save the recording
    return vad.save_to_wav(output_file)


def calibrate_microphone():
    """Helper function to calibrate silence threshold"""
    print("🔧 Microphone Calibration")
    print("Stay silent for 3 seconds...\n")
    
    duration = 3
    audio = sd.rec(int(duration * SAMPLE_RATE), 
                   samplerate=SAMPLE_RATE, 
                   channels=CHANNELS, 
                   dtype=DTYPE)
    sd.wait()
    
    # Calculate average amplitude
    rms = np.sqrt(np.mean(audio**2))
    suggested_threshold = rms * 3  # 3x the noise floor
    
    print(f"Ambient noise level: {rms:.2f}")
    print(f"Suggested threshold: {suggested_threshold:.2f}")
    print("\nNow speak for 3 seconds...\n")
    
    audio = sd.rec(int(duration * SAMPLE_RATE), 
                   samplerate=SAMPLE_RATE, 
                   channels=CHANNELS, 
                   dtype=DTYPE)
    sd.wait()
    
    speech_rms = np.sqrt(np.mean(audio**2))
    print(f"Speech level: {speech_rms:.2f}")
    
    if speech_rms > suggested_threshold:
        print(f"\n✅ Calibration successful!")
        print(f"Recommended threshold: {suggested_threshold:.0f}")
        return int(suggested_threshold)
    else:
        print(f"\n⚠️  Speech level too low, try speaking louder")
        return SILENCE_THRESHOLD


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Voice Activity Detection - Auto-stop Recording")
    print("=" * 60)
    
    # Ask if user wants to calibrate
    print("\nOptions:")
    print("1. Record with default settings")
    print("2. Calibrate microphone first (recommended)")
    print("3. Record with custom threshold")
    
    choice = input("\nChoice (1/2/3): ").strip()
    
    threshold = SILENCE_THRESHOLD
    
    if choice == "2":
        threshold = calibrate_microphone()
        input("\nPress Enter to start recording...")
    elif choice == "3":
        threshold = int(input("Enter silence threshold (default 500): ") or "500")
    
    # Get output filename
    output = input("\nOutput filename (default: recording.wav): ").strip() or "recording.wav"
    
    # Record
    print()
    success = record_until_silence(output, silence_threshold=threshold)
    
    if success:
        print(f"\n✅ Recording complete! Saved to: {output}")
        
        # Ask if user wants to play it back
        play = input("\nPlay recording? (y/n): ").strip().lower()
        if play == 'y':
            print("🔊 Playing...")
            data, sr = sf.read(output)
            sd.play(data, sr)
            sd.wait()
            print("✅ Playback complete")
    else:
        print("\n❌ Recording failed")
