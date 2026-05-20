import os
import wave
import threading
from datetime import datetime
from pathlib import Path
import uuid
import pyaudio
from faster_whisper import WhisperModel
import numpy as np
from fastapi import FastAPI

from App.general_utils.logging_config import get_logger


app = FastAPI()
logger = get_logger(__name__)

temp_dir = Path('temp')
temp_dir.mkdir(exist_ok=True)

def record_audio(
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        silence_threshold: int = 500,
        silence_duration: int = 5,
        max_record_time: int = 240,
) -> Path:
    
    audio = pyaudio.PyAudio()
    audio_file_path = temp_dir/f'audio_{uuid.uuid4().hex}.wav'

    stream = audio.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size
    )

    logger.info("audio_recording_started path=%s", audio_file_path)

    frames = []
    silent_chunks = 0

    chunk_per_second = sample_rate/ chunk_size
    max_silent_chunks = int(silence_duration * chunk_per_second)

    max_chunks = int(max_record_time * chunk_per_second)

    try:
        for _ in range(max_chunks):
            data = stream.read(chunk_size)
            frames.append(data)
            audio_data = np.frombuffer(data, dtype = np.int16)
            volume = np.abs(audio_data).mean()

            logger.debug("audio_recording_volume volume=%.2f", volume)

            if volume < silence_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0


            if silent_chunks > max_silent_chunks:
                logger.info("audio_recording_silence_detected path=%s", audio_file_path)
                break 

    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

    logger.info("audio_recording_stopped path=%s frames=%s", audio_file_path, len(frames))

    with wave.open(str(audio_file_path), 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
    
    return audio_file_path



def transcribe_audio(audio_file_path: Path) -> str:

    model = WhisperModel("medium", device="cpu", compute_type="int8")

    try:
        segments, info = model.transcribe(str(audio_file_path))

        text = " ".join(segment.text.strip() for segment in segments)

        return text.strip()
    
    finally:
        if audio_file_path.exists():
            audio_file_path.unlink()




def record_and_transcribe() -> str:

    audio_file_path = record_audio()
    transcription = transcribe_audio(audio_file_path)

    return transcription
