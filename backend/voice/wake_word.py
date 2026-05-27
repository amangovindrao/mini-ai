import os
import json
import time
import zipfile
import threading
import requests
import pyaudio
from vosk import Model, KaldiRecognizer

WAKE_WORDS = ["hey jarvis", "jarvis", "arre jarvis", "yo jarvis", "jarvis sun"]

class WakeWordDetector:
    def __init__(self, model_path="vosk-model-small-en-us-0.15"):
        self.model_path = model_path
        self.running = False
        self.thread = None
        
        # 1. Download Vosk model if not local
        if not os.path.exists(self.model_path):
            print(f"Vosk model folder '{self.model_path}' not found. Downloading...")
            url = "https://huggingface.co/rhasspy/vosk-models/resolve/main/en/vosk-model-small-en-us-0.15.zip"
            zip_path = "vosk-model-small-en-us-0.15.zip"
            try:
                r = requests.get(url, stream=True)
                r.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(".")
                print("Vosk model successfully downloaded and extracted.")
            except Exception as e:
                print(f"Error downloading Vosk model from mirror: {e}")
                # Fallback: Vosk will try its own automatic downloader internally if we pass name
            finally:
                if os.path.exists(zip_path):
                    try:
                        os.remove(zip_path)
                    except Exception:
                        pass

        # 2. Load Vosk model
        try:
            self.model = Model(self.model_path)
        except Exception:
            # Vosk Model loader fallback
            print("Failed loading via path, trying model_name fallback...")
            self.model = Model(model_name="vosk-model-small-en-us-0.15")

        self.rec = KaldiRecognizer(self.model, 16000)
        print("Vosk wake word model loaded successfully")

    def start(self, callback_fn):
        """
        Run the wake word detection in a daemon background thread so it never blocks.
        """
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._run_loop, 
            args=(callback_fn,), 
            daemon=True
        )
        self.thread.start()
        print("Wake word detector started in background thread")

    def stop(self):
        """
        Stop the detection loop cleanly.
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None

    def _run_loop(self, callback_fn):
        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4000
            )
            stream.start_stream()
        except Exception as e:
            print(f"Error opening microphone for wake word detector: {e}")
            p.terminate()
            self.running = False
            return

        while self.running:
            try:
                data = stream.read(2000, exception_on_overflow=False)
                if len(data) == 0:
                    time.sleep(0.01)
                    continue

                # Process buffer
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = res.get("text", "")
                else:
                    res = json.loads(self.rec.PartialResult())
                    text = res.get("partial", "")

                if text:
                    text_lower = text.lower()
                    matched = False
                    for wake in WAKE_WORDS:
                        if wake in text_lower:
                            matched = True
                            break
                    
                    if matched:
                        print("WAKE WORD DETECTED")
                        self.rec.Reset()
                        # Run callback in a daemon thread so it doesn't block Vosk detection
                        threading.Thread(target=callback_fn, daemon=True).start()
                        
                        # Wait 2 seconds before listening again to avoid double-triggering
                        time.sleep(2.0)
                        self.rec.Reset()
                        
            except Exception as e:
                print(f"Exception in wake word loop: {e}")
                time.sleep(0.1)

        # Cleanup
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        p.terminate()
