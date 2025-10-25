
import wave

def wav_to_bytes(file_path):
    """
    Reads a WAV file and returns its content as a bytes object.

    Args:
        file_path (str): The path to the WAV file.

    Returns:
        bytes: The binary content of the WAV file.
    """
    try:
        with open(file_path, "rb") as f:
            wav_data = f.read()
        return wav_data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def bytes_to_wav(audio_bytes, filename, nchannels, sampwidth, framerate):
    """
    Converts raw audio bytes to a WAV file.

    Args:
        audio_bytes (bytes): The raw audio data as a bytes object.
        filename (str): The name of the output WAV file.
        nchannels (int): The number of audio channels (e.g., 1 for mono, 2 for stereo).
        sampwidth (int): The sample width in bytes (e.g., 2 for 16-bit audio).
        framerate (int): The sample rate in Hz (e.g., 44100).
    """
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(nchannels)
        wav_file.setsampwidth(sampwidth)
        wav_file.setframerate(framerate)
        wav_file.writeframes(audio_bytes)