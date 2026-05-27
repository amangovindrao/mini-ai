import sqlite3
import os
import json
import math
from typing import List, Tuple, Optional, Any, Dict
from datetime import datetime
from dotenv import load_dotenv

# Load env variables for DB_PATH
load_dotenv()
DB_PATH = os.getenv("DB_PATH", "./database/jarvis.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _base_where(user_id: int, column_name: str = "user_id") -> Tuple[str, List[Any]]:
    """Enforces access control. Admin (id=1) sees everything."""
    if user_id == 1:
        return "1=1", []
    return f"{column_name} = ?", [user_id]

# ==========================================
# USERS
# ==========================================

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Returns the user profile for the given user_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users(admin_id: int = 1) -> List[Dict]:
    """Admin only. Returns all users."""
    if admin_id != 1:
        raise PermissionError("Admin only access")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==========================================
# FACE EMBEDDINGS
# ==========================================

def save_face_embedding(user_id: int, embedding_blob: bytes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO face_embeddings (user_id, embedding_blob)
        VALUES (?, ?)
    """, (user_id, embedding_blob))
    conn.commit()
    conn.close()

def get_all_embeddings() -> List[Tuple[int, bytes]]:
    """Returns list of (user_id, embedding)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, embedding_blob FROM face_embeddings")
    rows = cursor.fetchall()
    conn.close()
    return [(r["user_id"], r["embedding_blob"]) for r in rows]

def get_user_by_face(embedding_vector: List[float]) -> Optional[Dict]:
    """Cosine similarity match to find user by face embedding."""
    all_embeddings = get_all_embeddings()
    best_user_id = None
    best_score = -1.0
    
    def cosine_sim(v1, v2):
        dot = sum(a*b for a,b in zip(v1,v2))
        norm1 = math.sqrt(sum(a*a for a in v1))
        norm2 = math.sqrt(sum(b*b for b in v2))
        if norm1 == 0 or norm2 == 0: return 0.0
        return dot / (norm1 * norm2)

    for uid, emb_blob in all_embeddings:
        if not emb_blob:
            continue
        try:
            # Assumes embedding_blob was stored as a JSON string
            if isinstance(emb_blob, bytes):
                saved_vector = json.loads(emb_blob.decode('utf-8'))
            else:
                saved_vector = json.loads(emb_blob)
            
            score = cosine_sim(embedding_vector, saved_vector)
            if score > best_score:
                best_score = score
                best_user_id = uid
        except Exception:
            continue
            
    # Assuming threshold logic can be applied here, e.g. > 0.85
    if best_user_id is not None and best_score > 0.85:
        return get_user_by_id(best_user_id)
    return None

# ==========================================
# CONVERSATIONS
# ==========================================

def save_conversation(user_id: int, message: str, response: str, language: str, emotion: str, confidence: float, ms: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversations 
        (user_id, message, response, language, emotion, confidence_score, processing_time_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, message, response, language, emotion, confidence, ms))
    conn.commit()
    conn.close()

def get_conversations(user_id: int, limit: int = 50) -> List[Dict]:
    where_clause, params = _base_where(user_id)
    
    conn = get_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM conversations WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==========================================
# USER MEMORY
# ==========================================

def save_memory(user_id: int, type: str, content: str, importance: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_memory (user_id, memory_type, content, importance_score)
        VALUES (?, ?, ?, ?)
    """, (user_id, type, content, importance))
    conn.commit()
    conn.close()

# ==========================================
# PENDING LEARNING
# ==========================================

def get_pending_questions(user_id: int, limit: int = 20) -> List[Dict]:
    where_clause, params = _base_where(user_id, column_name="asked_by_user_id")
    
    conn = get_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM pending_learning WHERE {where_clause} AND status = 'pending' ORDER BY frequency_count DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_question_answered(question_id: int, answer: str, admin_id: int = 1):
    if admin_id != 1:
        raise PermissionError("Only admin can answer pending questions")
    
    conn = get_connection()
    cursor = conn.cursor()
    # 'answer' might be saved inside similar_questions_json or handled separately in learned_responses
    # Here we just update the status to mark it as answered.
    cursor.execute("""
        UPDATE pending_learning 
        SET status = 'answered', last_asked_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (question_id,))
    conn.commit()
    conn.close()

# ==========================================
# LEARNED RESPONSES
# ==========================================

def save_learned_response(trigger_phrases: str, response: str, language: str, emotion: str, func_name: str, file_path: str, admin_id: int = 1):
    if admin_id != 1:
        raise PermissionError("Only admin can create learned responses")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO learned_responses 
        (trigger_phrases_json, response_template, language, emotion_tone, code_function_name, code_file_path, created_by_admin, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (trigger_phrases, response, language, emotion, func_name, file_path, admin_id))
    conn.commit()
    conn.close()

def get_active_learned_responses(user_id: int = 1) -> List[Dict]:
    # Learned responses are active and visible globally, but we include user_id just to follow conventions
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM learned_responses WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==========================================
# ADMIN NOTIFICATIONS
# ==========================================

def add_admin_notification(type: str, message: str, related_id: int, user_id: int = 1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admin_notifications (type, message, related_id)
        VALUES (?, ?, ?)
    """, (type, message, related_id))
    conn.commit()
    conn.close()

def get_unread_notifications(user_id: int = 1) -> List[Dict]:
    if user_id != 1:
        raise PermissionError("Admin only access")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_notifications WHERE is_read = 0 ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

