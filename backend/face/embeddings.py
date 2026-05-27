import sqlite3
import pickle
import os
import time
import numpy as np
import cv2
import insightface
from insightface.app import FaceAnalysis

# Global app instance to avoid reloading models on every call
_face_app = None

def get_face_analysis_app():
    global _face_app
    if _face_app is None:
        # buffalo_l is the model package name
        # We specify providers=['CPUExecutionProvider'] for CPU compatibility
        _face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        _face_app.prepare(ctx_id=-1, det_size=(640, 640))
    return _face_app

def extract_embedding(frame):
    """
    Detects faces in the frame using buffalo_l model.
    Returns the 512-float numpy array for the largest face.
    Returns None if no face is detected.
    """
    app = get_face_analysis_app()
    faces = app.get(frame)
    if not faces:
        return None
        
    # Find the largest face by bounding box area
    largest_face = None
    largest_area = 0
    for face in faces:
        bbox = face.bbox  # [x1, y1, x2, y2]
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if area > largest_area:
            largest_area = area
            largest_face = face
            
    if largest_face is not None:
        return largest_face.embedding
    return None

def save_embedding(user_id, frame, db_path):
    """
    Extracts face embedding, serializes it using pickle, 
    saves it to SQLite DB, and saves the image to faces/ folder.
    Returns True on success, False if no face is detected.
    """
    embedding = extract_embedding(frame)
    if embedding is None:
        return False
        
    # Create the faces directory if it doesn't exist
    faces_dir = os.path.join(os.path.dirname(db_path), "..", "faces")
    faces_dir = os.path.abspath(faces_dir)
    os.makedirs(faces_dir, exist_ok=True)
    
    timestamp = int(time.time())
    photo_name = f"{user_id}_{timestamp}.jpg"
    photo_path = os.path.join(faces_dir, photo_name)
    
    # Save image as JPG
    cv2.imwrite(photo_path, frame)
    
    # Serialize embedding
    serialized_embedding = pickle.dumps(embedding)
    
    # Save to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO face_embeddings (user_id, embedding_blob, photo_path, confidence)
        VALUES (?, ?, ?, ?)
    """, (user_id, serialized_embedding, photo_path, 1.0))
    conn.commit()
    conn.close()
    
    return True

def load_all_embeddings(db_path):
    """
    Loads all saved face embeddings from SQLite.
    Returns a list of tuples: (user_id, numpy_array).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, embedding_blob FROM face_embeddings")
    rows = cursor.fetchall()
    conn.close()
    
    embeddings = []
    for user_id, blob in rows:
        if blob:
            try:
                emb_array = pickle.loads(blob)
                embeddings.append((user_id, emb_array))
            except Exception:
                continue
    return embeddings

def match_face(frame, db_path):
    """
    Extracts embedding from frame and matches it against database profiles using cosine similarity.
    Returns (user_id, score) if a match exceeds 0.85, else None.
    """
    new_emb = extract_embedding(frame)
    if new_emb is None:
        return None
        
    stored_embs = load_all_embeddings(db_path)
    if not stored_embs:
        return None
        
    best_score = -1.0
    best_user_id = None
    
    norm_new = np.linalg.norm(new_emb)
    if norm_new == 0:
        return None
        
    for user_id, stored_emb in stored_embs:
        norm_stored = np.linalg.norm(stored_emb)
        if norm_stored == 0:
            continue
            
        # Cosine similarity formula: dot(A, B) / (||A|| * ||B||)
        similarity = np.dot(new_emb, stored_emb) / (norm_new * norm_stored)
        if similarity > best_score:
            best_score = similarity
            best_user_id = user_id
            
    if best_score > 0.85:
        return (best_user_id, float(best_score))
    return None
