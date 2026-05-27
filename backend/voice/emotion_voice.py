from datetime import datetime, time

# Emotion keyword mapping dictionary
EMOTION_KEYWORDS = {
    "urgent": ["jaldi", "emergency", "abhi", "turant", "quick", "asap"],
    "happy": ["badhiya", "awesome", "great", "khushi", "maza", "yay"],
    "sad": ["sad", "dukhi", "bura laga", "pareshan", "tension"],
    "sarcastic": ["haan bilkul", "sure sure", "of course", "obviously"],
    "caring": ["theek ho", "sab theek", "help", "pareshani", "chinta"]
}

# Parameters per emotion
EMOTION_PARAMS = {
    "calm": {
        "speed_multiplier": 1.00,
        "filler_word": "Hmm...",
        "pause_ms": 500,
        "intensity": 0.5
    },
    "happy": {
        "speed_multiplier": 1.15,
        "filler_word": "Yay...",
        "pause_ms": 300,
        "intensity": 0.8
    },
    "sad": {
        "speed_multiplier": 0.80,
        "filler_word": "Hmm...",
        "pause_ms": 800,
        "intensity": 0.3
    },
    "urgent": {
        "speed_multiplier": 1.25,
        "filler_word": "Dekho...",
        "pause_ms": 100,
        "intensity": 0.9
    },
    "sarcastic": {
        "speed_multiplier": 0.90,
        "filler_word": "Well...",
        "pause_ms": 600,
        "intensity": 0.6
    },
    "caring": {
        "speed_multiplier": 0.85,
        "filler_word": "Suno...",
        "pause_ms": 400,
        "intensity": 0.4
    }
}

def detect_emotion(text: str) -> str:
    """
    Detect emotion from the input text by counting keyword matches.
    Returns the emotion with the most matches, or "calm" as default.
    """
    if not text:
        return "calm"
        
    text_lower = text.lower()
    scores = {emotion: 0 for emotion in EMOTION_KEYWORDS.keys()}
    
    # Count occurrences of keywords
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            # Check for substring match in lowercase text
            scores[emotion] += text_lower.count(keyword)
            
    # Find emotion with max score
    max_score = 0
    detected_emotion = "calm"
    
    for emotion, score in scores.items():
        if score > max_score:
            max_score = score
            detected_emotion = emotion
            
    return detected_emotion

def get_voice_params(emotion: str, time_of_day=None) -> dict:
    """
    Return voice parameters: { speed_multiplier, filler_word, pause_ms, intensity }
    Important: If local time is late night (after 10 PM / 22:00 or before 6 AM), 
    always return calm params regardless of what emotion was detected.
    """
    # Parse time_of_day to get the hour
    hour = None
    if time_of_day is None:
        hour = datetime.now().hour
    elif isinstance(time_of_day, int):
        hour = time_of_day
    elif isinstance(time_of_day, (datetime, time)):
        hour = time_of_day.hour
    elif isinstance(time_of_day, str):
        try:
            # Handle "23:15", "10 PM", etc.
            if ":" in time_of_day:
                hour = int(time_of_day.split(":")[0])
            else:
                hour = int(time_of_day)
        except ValueError:
            hour = datetime.now().hour
    else:
        hour = datetime.now().hour

    # Late night rule: after 10 PM (22:00) or before 6 AM
    is_late_night = (hour >= 22 or hour < 6)
    
    if is_late_night:
        print(f"Late night detected (hour {hour}), forcing 'calm' voice parameters.")
        return EMOTION_PARAMS["calm"]
        
    return EMOTION_PARAMS.get(emotion, EMOTION_PARAMS["calm"])
