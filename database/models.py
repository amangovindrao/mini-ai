from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    id: Optional[int] = None
    name: str = ""
    role: str = "user"
    language_pref: str = "hinglish"
    personality_style: str = "casual"
    energy_level: str = "medium"
    humor_type: str = "light"
    nickname: Optional[str] = None
    face_registered: bool = False
    voice_registered: bool = False
    created_at: Optional[datetime] = None

    def __post_init__(self):
        valid_roles = {"admin", "user", "guest", "child"}
        if self.role not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")

@dataclass
class FaceEmbedding:
    id: Optional[int] = None
    user_id: int = 0
    embedding_blob: Optional[bytes] = None
    photo_path: Optional[str] = None
    confidence: Optional[float] = None
    captured_at: Optional[datetime] = None

@dataclass
class Conversation:
    id: Optional[int] = None
    user_id: int = 0
    message: Optional[str] = None
    response: Optional[str] = None
    language: Optional[str] = None
    emotion: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    timestamp: Optional[datetime] = None

@dataclass
class UserMemory:
    id: Optional[int] = None
    user_id: int = 0
    memory_type: Optional[str] = None
    content: Optional[str] = None
    importance_score: float = 0.5
    embedding_blob: Optional[bytes] = None
    created_at: Optional[datetime] = None

@dataclass
class PersonalityProfile:
    id: Optional[int] = None
    user_id: int = 0
    tone: Optional[str] = None
    speed: Optional[str] = None
    slang_bank: Optional[str] = None
    references_json: Optional[str] = None
    filler_words: Optional[str] = None
    language_mix_ratio: str = "60:40"
    updated_at: Optional[datetime] = None

@dataclass
class Task:
    id: Optional[int] = None
    user_id: int = 0
    title: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    reminder_time: Optional[datetime] = None
    created_at: Optional[datetime] = None

@dataclass
class PendingLearning:
    id: Optional[int] = None
    asked_by_user_id: int = 0
    original_question: Optional[str] = None
    similar_questions_json: Optional[str] = None
    frequency_count: int = 1
    first_asked_at: Optional[datetime] = None
    last_asked_at: Optional[datetime] = None
    status: str = "pending"

@dataclass
class LearnedResponse:
    id: Optional[int] = None
    trigger_phrases_json: Optional[str] = None
    response_template: Optional[str] = None
    language: str = "hinglish"
    emotion_tone: str = "calm"
    code_function_name: Optional[str] = None
    code_file_path: Optional[str] = None
    created_by_admin: Optional[int] = None
    is_active: bool = False
    created_at: Optional[datetime] = None

@dataclass
class CodeSandbox:
    id: Optional[int] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    allowed_to_edit: bool = False
    last_modified: Optional[datetime] = None
    modified_by: Optional[str] = None
    backup_path: Optional[str] = None

@dataclass
class AdminNotification:
    id: Optional[int] = None
    type: Optional[str] = None
    message: Optional[str] = None
    related_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
