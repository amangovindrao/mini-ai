import os
import re
import time
import random
import numpy as np
import simpleaudio as sa
from TTS.api import TTS

# Define dictionaries at the top
VOICE_MODELS = {
    "male": os.getenv("MALE_VOICE_MODEL", "tts_models/multilingual/multi-dataset/your_tts"),
    "female": os.getenv("FEMALE_VOICE_MODEL", "tts_models/multilingual/multi-dataset/your_tts")
}

EMOTION_SPEED = {
    "happy": 1.15,
    "sad": 0.80,
    "calm": 1.00,
    "urgent": 1.25,
    "sarcastic": 0.90,
    "caring": 0.85
}

FILLER_WORDS = {
    "hinglish": ["Hmm...", "Haan toh...", "Dekho...", "Suno..."],
    "hindi": ["Haan...", "Theek hai...", "Suno ji..."],
    "english": ["Hmm...", "Well...", "Let me see..."],
    "bhojpuri": ["Haan beta...", "Theek ba...", "Suno raja..."]
}

class TextToSpeech:
    def __init__(self, voice="male"):
        self.voice_name = voice
        self.model_name = VOICE_MODELS.get(voice, "tts_models/multilingual/multi-dataset/your_tts")
        print(f"Initializing TTS with voice model: {self.model_name}")
        self.tts = TTS(model_name=self.model_name, gpu=False)
        print("TTS model loaded and ready")

    def _get_speaker_wav(self, emotion):
        """
        Retrieves speaker reference WAV for YourTTS voice cloning.
        Look for any WAV file in:
          1. voice_data/{voice}/{emotion}/
          2. voice_data/{voice}/calm/
          3. Recursive search in voice_data/{voice}/
          4. Simpleaudio package test audios
        """
        # 1. Specific emotion folder
        dir_path = os.path.join("voice_data", self.voice_name, emotion)
        if os.path.isdir(dir_path):
            wav_files = [f for f in os.listdir(dir_path) if f.endswith(".wav")]
            if wav_files:
                return os.path.join(dir_path, wav_files[0])

        # 2. Fallback to calm folder
        dir_path_calm = os.path.join("voice_data", self.voice_name, "calm")
        if os.path.isdir(dir_path_calm):
            wav_files = [f for f in os.listdir(dir_path_calm) if f.endswith(".wav")]
            if wav_files:
                return os.path.join(dir_path_calm, wav_files[0])

        # 3. Recursive search
        dir_path_general = os.path.join("voice_data", self.voice_name)
        if os.path.isdir(dir_path_general):
            for root, dirs, files in os.walk(dir_path_general):
                wav_files = [f for f in files if f.endswith(".wav")]
                if wav_files:
                    return os.path.join(root, wav_files[0])

        # 4. Ultimate fallback to package test wav to prevent crashing
        fallback_paths = [
            r"C:\JARVIS-AI\venv\Lib\site-packages\simpleaudio\test_audio\c.wav",
            r"C:\JARVIS-AI\venv\Lib\site-packages\simpleaudio\test_audio\left_right.wav"
        ]
        for p in fallback_paths:
            if os.path.exists(p):
                return p
                
        return None

    def speak(self, text, emotion="calm", language="hinglish", add_filler=True):
        """
        Synthesizes the text and plays it sentence-by-sentence to stream voice output.
        """
        total_start_time = time.time()
        
        # 1. Prepend filler if needed
        if add_filler and len(text) > 50:
            lang_key = language.lower() if language.lower() in FILLER_WORDS else "english"
            filler = random.choice(FILLER_WORDS[lang_key])
            text = f"{filler} {text}"
            print(f"Prepended filler word: '{filler}'")

        # 2. Split text into sentences
        # Regex splits on standard punctuation (.?!।), followed by whitespace
        sentences = re.split(r'(?<=[.!?।])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return

        print(f"TTS splitting text into {len(sentences)} sentences for streaming...")

        # 3. Prepare parameters based on model type
        tts_kwargs = {}
        if self.tts.is_multi_lingual:
            # Map request language to YourTTS supported languages (en, fr, pt)
            lang_map = {
                "hinglish": "en",
                "english": "en",
                "hindi": "en",
                "bhojpuri": "en"
            }
            mapped_lang = lang_map.get(language.lower(), "en")
            if self.tts.languages and mapped_lang in self.tts.languages:
                tts_kwargs["language"] = mapped_lang
            elif self.tts.languages:
                tts_kwargs["language"] = self.tts.languages[0]

        if self.tts.is_multi_speaker:
            speaker_wav = self._get_speaker_wav(emotion)
            if speaker_wav:
                tts_kwargs["speaker_wav"] = speaker_wav
                print(f"Using cloning reference speaker: {speaker_wav}")
            elif self.tts.speakers:
                tts_kwargs["speaker"] = self.tts.speakers[0]

        # 4. Synthesize and play sentence-by-sentence (streaming overlap)
        play_objs = []
        speed_multiplier = EMOTION_SPEED.get(emotion, 1.00)
        output_sample_rate = self.tts.synthesizer.output_sample_rate
        play_rate = int(output_sample_rate * speed_multiplier)

        for i, sentence in enumerate(sentences):
            print(f"Generating sentence {i+1}/{len(sentences)}: '{sentence}'")
            gen_start = time.time()
            
            # Synthesize sentence
            wav = self.tts.tts(sentence, **tts_kwargs)
            audio_data = np.array(wav)
            
            # Scale float range [-1.0, 1.0] to 16-bit PCM integer range
            audio_data = (audio_data * 32767).astype(np.int16)
            gen_time = time.time() - gen_start
            print(f"Generated sentence {i+1} in {gen_time:.2f}s")
            
            # Wait for previous sentence to finish playing before starting the next
            if play_objs:
                play_objs[-1].wait_done()
                
            # Play current sentence asynchronously
            play_obj = sa.play_buffer(
                audio_data, 
                num_channels=1, 
                bytes_per_sample=2, 
                sample_rate=play_rate
            )
            play_objs.append(play_obj)

        # Wait for the very last sentence to finish playing
        if play_objs:
            play_objs[-1].wait_done()
            
        total_time = time.time() - total_start_time
        print(f"TTS speak completed. Total time (gen + play): {total_time:.2f}s")

if __name__ == "__main__":
    # Test block to run directly
    import os
    tts = TextToSpeech(voice="male")
    test_phrase = "Hello. JARVIS Text to Speech system is fully operational."
    tts.speak(test_phrase, emotion="calm", language="english", add_filler=True)
