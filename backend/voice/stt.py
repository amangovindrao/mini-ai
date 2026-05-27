import os
import wave
import math
import tempfile
import collections
import pyaudio
import webrtcvad
import whisper

class SpeechToText:
    def __init__(self, model_size="small"):
        print(f"Loading Whisper model '{model_size}'...")
        self.model = whisper.load_model(model_size)
        print("Whisper model loaded")

    def transcribe_file(self, path) -> dict:
        """
        Transcribe any existing WAV or MP3 file.
        Returns: { "text": str, "language": str, "confidence": float }
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")

        result = self.model.transcribe(path, language=None)
        
        # Calculate average confidence based on segment probabilities
        segments = result.get("segments", [])
        if segments:
            avg_prob = sum(math.exp(s.get("avg_logprob", 0)) for s in segments) / len(segments)
        else:
            avg_prob = 1.0
        
        avg_prob = min(1.0, max(0.0, avg_prob))
        
        return {
            "text": result.get("text", "").strip(),
            "language": result.get("language", ""),
            "confidence": float(avg_prob)
        }

    def listen_and_transcribe(self, timeout=10.0) -> dict:
        """
        Open microphone using PyAudio.
        Use webrtcvad (Voice Activity Detection) to detect when speaker starts and stops.
        Stop recording after 1.5 seconds of silence.
        Save audio to a temporary WAV file.
        Transcribe the saved WAV file.
        Returns: { "text": str, "language": str, "confidence": float }
        """
        # Audio configuration
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        FRAME_DURATION_MS = 30
        CHUNK_SIZE = int(RATE * FRAME_DURATION_MS / 1000) # 480 samples

        # Initialize WebRTC VAD (mode 3 is most aggressive/sensitive to speech)
        vad = webrtcvad.Vad(3)

        p = pyaudio.PyAudio()
        try:
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
        except Exception as e:
            print(f"Error opening microphone stream: {e}")
            return {"text": "", "language": "", "confidence": 0.0}

        print("Listening...")
        
        # Sliding ring buffer for history (keep 450ms of audio, i.e., 15 frames of 30ms)
        history_len = 15
        history_buffer = collections.deque(maxlen=history_len)
        
        recorded_frames = []
        is_speaking = False
        consecutive_silent_frames = 0
        silence_threshold_frames = int(1500 / FRAME_DURATION_MS) # 1.5s = 50 frames
        
        # To avoid infinite waiting, set a timeout
        max_wait_frames = int(timeout * 1000 / FRAME_DURATION_MS)
        wait_counter = 0

        stream.start_stream()

        try:
            while True:
                try:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                except Exception as e:
                    print(f"Warning: input overflow or read error: {e}")
                    continue

                if len(data) == 0:
                    continue

                is_speech = vad.is_speech(data, RATE)

                if not is_speaking:
                    history_buffer.append(data)
                    # Simple trigger: if more than 50% of the ring buffer is speech, start recording
                    speech_frames = sum(1 for f in history_buffer if vad.is_speech(f, RATE))
                    if speech_frames > (history_len // 2):
                        is_speaking = True
                        print("Speech detected, recording...")
                        # Append the pre-roll history frames to start cleanly
                        recorded_frames.extend(history_buffer)
                    else:
                        wait_counter += 1
                        if wait_counter >= max_wait_frames:
                            print("Listening timeout - no speech detected.")
                            break
                else:
                    recorded_frames.append(data)
                    if not is_speech:
                        consecutive_silent_frames += 1
                        if consecutive_silent_frames >= silence_threshold_frames:
                            print("Silence detected, finishing recording.")
                            break
                    else:
                        consecutive_silent_frames = 0

        finally:
            # Clean up PyAudio resources safely
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
            p.terminate()

        if not recorded_frames:
            return {"text": "", "language": "", "confidence": 0.0}

        # Save to temp WAV file
        temp_wav_fd, temp_wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_wav_fd)

        try:
            wf = wave.open(temp_wav_path, "wb")
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(recorded_frames))
            wf.close()

            # Transcribe
            result = self.transcribe_file(temp_wav_path)
            return result
        finally:
            if os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except Exception:
                    pass

if __name__ == "__main__":
    stt = SpeechToText()
    print("Microphone listening... Speak now.")
    res = stt.listen_and_transcribe()
    print("Transcription result:")
    print(res)
