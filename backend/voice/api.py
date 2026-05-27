import asyncio
import time
import numpy as np
import pyaudio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

from backend.voice.stt import SpeechToText
from backend.voice.tts import TextToSpeech

router = APIRouter(prefix="/voice")

# Global status variable: "idle", "listening", or "speaking"
current_status = "idle"

# Lazy-loaded STT and TTS engines
stt_engine: Optional[SpeechToText] = None
tts_engines = {}

def get_stt() -> SpeechToText:
    """Helper to lazily load and return the SpeechToText engine."""
    global stt_engine
    if stt_engine is None:
        stt_engine = SpeechToText()
    return stt_engine

def get_tts(voice: str) -> TextToSpeech:
    """Helper to lazily load and return the TextToSpeech engine for a specific voice."""
    global tts_engines
    if voice not in tts_engines:
        tts_engines[voice] = TextToSpeech(voice=voice)
    return tts_engines[voice]


class SpeakRequest(BaseModel):
    text: str
    emotion: str = "calm"
    voice: str = "male"
    language: str = "hinglish"


@router.post("/listen")
async def post_listen():
    """
    Start recording from microphone and return the transcript dict.
    """
    global current_status
    current_status = "listening"
    try:
        stt = get_stt()
        # run blocking microphone recording in a thread pool
        result = await asyncio.to_thread(stt.listen_and_transcribe)
        return result
    except Exception as e:
        print(f"Error during listen endpoint: {e}")
        return {"text": "", "language": "", "confidence": 0.0, "error": str(e)}
    finally:
        current_status = "idle"


@router.post("/speak")
async def post_speak(req: SpeakRequest):
    """
    Synthesize text to speech using the selected parameters and play it.
    Returns how many milliseconds the generation and playback took.
    """
    global current_status
    current_status = "speaking"
    try:
        tts = get_tts(req.voice)
        start_time = time.time()
        # run blocking audio synthesis and playback in a thread pool
        await asyncio.to_thread(
            tts.speak, 
            req.text, 
            emotion=req.emotion, 
            language=req.language, 
            add_filler=True
        )
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {"time_ms": elapsed_ms}
    except Exception as e:
        print(f"Error during speak endpoint: {e}")
        return {"time_ms": 0, "error": str(e)}
    finally:
        current_status = "idle"


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket that streams real-time microphone audio level data.
    Used by the frontend VoiceWave component to show the waveform.
    """
    await websocket.accept()
    
    p = pyaudio.PyAudio()
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK_SIZE = 512
    
    # Try opening input stream
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        stream.start_stream()
    except Exception as e:
        print(f"WS /voice/stream: Error opening microphone stream: {e}")
        await websocket.close()
        p.terminate()
        return

    try:
        while True:
            # Read input audio data chunk in a thread
            data = await asyncio.to_thread(stream.read, CHUNK_SIZE, False)
            if not data:
                continue
                
            # Convert bytes to short samples
            samples = np.frombuffer(data, dtype=np.int16)
            
            # Compute Root Mean Square (RMS) as volume level
            rms = np.sqrt(np.mean(samples.astype(np.float32)**2)) if len(samples) > 0 else 0
            
            # Normalize level to a 0-100 scale (with a multiplier boost for visual clarity)
            normalized_level = min(100.0, (rms / 32767.0) * 100.0 * 5.0)
            
            # Send level to client
            await websocket.send_json({
                "level": float(normalized_level),
                "raw_rms": float(rms)
            })
            
            # Frame rate control (~30 frames/sec)
            await asyncio.sleep(0.03)
            
    except WebSocketDisconnect:
        print("WS /voice/stream: Client disconnected")
    except Exception as e:
        print(f"WS /voice/stream: Exception: {e}")
    finally:
        # Resource cleanup
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        p.terminate()


@router.get("/status")
async def get_status():
    """
    Return current voice system state: "speaking" or "listening" or "idle".
    """
    return {"status": current_status}
