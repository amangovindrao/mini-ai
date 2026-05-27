import sqlite3
import cv2
import time
import os
from backend.face.embeddings import save_embedding

def register_new_user(name: str, role: str, language: str, db_path: str) -> int:
    """
    Guides a user to register their face in the system by taking 5 different photos at various angles.
    Inserts the user into the SQLite database, captures frames, extracts face embeddings, 
    and saves them. Marks the user profile as face_registered.
    """
    # Step 1: Insert user into users table and get the new user_id
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, role, language_pref, face_registered)
        VALUES (?, ?, ?, 0)
    """, (name, role, language))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Step 2: Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera for registration.")

    # Angle prompts and messages
    prompts = [
        "Photo 1: Seedha camera mein dekho",
        "Photo 2: Thoda left turn karo",
        "Photo 3: Thoda right turn karo",
        "Photo 4: Thoda upar dekho",
        "Photo 5: Natural raho, relax karo"
    ]

    successful_captures = 0

    try:
        # Step 3: Guide the user and capture each angle
        for i, prompt in enumerate(prompts):
            print(f"\n[JARVIS-AI Registration] {prompt}")
            # Wait 2 seconds
            time.sleep(2)
            
            # Clear buffer by reading a few frames
            for _ in range(5):
                cap.read()
                
            ret, frame = cap.read()
            if not ret:
                print(f"Error: Failed to capture frame for Photo {i+1}")
                continue
                
            # Attempt to save the face embedding
            success = save_embedding(user_id, frame, db_path)
            if success:
                successful_captures += 1
                print(f"Angle {i+1} saved successfully.")
            else:
                print(f"Angle {i+1} failed: No face detected. Please position yourself correctly.")
                
        # If at least one angle succeeded, mark user as face_registered = 1
        if successful_captures > 0:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET face_registered = 1 WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            print(f"\nRegistered! User ID: {user_id}")
        else:
            print(f"\nRegistration incomplete. No faces detected across any angles.")
            
    finally:
        cap.release()
        
    return user_id

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    # Fix relative imports when running as a module directly
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    load_dotenv()
    default_db_path = os.getenv("DB_PATH", "./database/jarvis.db")

    parser = argparse.ArgumentParser(description="JARVIS-AI Face Registration")
    parser.add_argument("--name", required=True, help="User name")
    parser.add_argument("--role", required=True, help="User role (e.g., admin, user)")
    parser.add_argument("--language", required=True, help="Preferred language")
    
    args = parser.parse_args()
    register_new_user(args.name, args.role, args.language, default_db_path)
