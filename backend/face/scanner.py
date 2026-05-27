import cv2
import time
import random
import asyncio
import sqlite3
import numpy as np
from typing import Dict, Any, Optional, Callable
from backend.face.embeddings import match_face, extract_embedding

TIMEOUT_LINES = [
    "Bhai camera mein aao theek se, scan nahi ho raha...",
    "Arre yaar, pehchaan nahi paya — naam batao?",
    "Face scan failed. Kaun ho tum? Bolo toh...",
    "Hmm... system confused hai. Apna naam bolo please",
    "Yaar andhere mein ho kya? Dikhte nahi...",
    "Oye! Camera ke saamne aao theek se"
]

NO_MATCH_LINES = [
    "Naya chehra hai. Register karna chahoge?",
    "Tumhe pehle nahi dekha — kaun ho tum?",
    "Database mein nahi ho — register karo"
]

class FaceScanner:
    def __init__(self, db_path: str, websocket_emitter: Optional[Callable[[Dict[str, Any]], Any]] = None):
        self.db_path = db_path
        self.websocket_emitter = websocket_emitter

    async def _emit(self, data: Dict[str, Any]):
        if self.websocket_emitter:
            try:
                if asyncio.iscoroutinefunction(self.websocket_emitter):
                    await self.websocket_emitter(data)
                else:
                    self.websocket_emitter(data)
            except Exception as e:
                print(f"Error emitting websocket message: {e}")

    def _get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    async def scan(self, timeout: float = 12.0) -> Optional[Dict[str, Any]]:
        """
        Runs the camera face scanning loop. Matches frames against database profiles.
        Emits progress and confirmation events via WebSocket.
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            await self._emit({"status": "error", "message": "Could not open camera"})
            return None

        start_time = time.time()
        last_check_time = 0.0
        face_seen_at_least_once = False

        try:
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.05)
                    continue

                current_time = time.time()
                elapsed = current_time - start_time
                progress = min(100, int((elapsed / timeout) * 100))

                # Capture and run matching every 0.5 seconds
                if current_time - last_check_time >= 0.5:
                    last_check_time = current_time
                    
                    # Run face detection/extraction in thread pool to avoid blocking async loop
                    embedding = await asyncio.to_thread(extract_embedding, frame)
                    face_detected = (embedding is not None)
                    
                    if face_detected:
                        face_seen_at_least_once = True
                        
                        # Match the embedding against stored embeddings
                        match_res = await asyncio.to_thread(self._match_embedding, embedding)
                        if match_res:
                            user_id, score = match_res
                            profile = self._get_user_profile(user_id)
                            if profile:
                                await self._emit({
                                    "status": "confirmed",
                                    "user": profile
                                })
                                return profile

                    # Emit active scanning progress update
                    await self._emit({
                        "status": "scanning",
                        "progress": progress,
                        "face_detected": face_detected
                    })

                # Short delay to prevent CPU spinning
                await asyncio.sleep(0.05)

            # Timer expired - analyze match state
            if not face_seen_at_least_once:
                chosen_line = random.choice(TIMEOUT_LINES)
                await self._emit({
                    "status": "timeout",
                    "message": chosen_line
                })
            else:
                chosen_line = random.choice(NO_MATCH_LINES)
                await self._emit({
                    "status": "unknown",
                    "message": chosen_line
                })

            return None

        finally:
            cap.release()

    def _match_embedding(self, new_emb: np.ndarray) -> Optional[tuple]:
        """Runs cosine similarity calculation on pre-extracted embedding against DB."""
        from backend.face.embeddings import load_all_embeddings
        stored = load_all_embeddings(self.db_path)
        if not stored:
            return None
            
        best_score = -1.0
        best_user_id = None
        
        norm_new = np.linalg.norm(new_emb)
        if norm_new == 0:
            return None
            
        for user_id, stored_emb in stored:
            norm_stored = np.linalg.norm(stored_emb)
            if norm_stored == 0:
                continue
                
            similarity = np.dot(new_emb, stored_emb) / (norm_new * norm_stored)
            if similarity > best_score:
                best_score = similarity
                best_user_id = user_id
                
        if best_score > 0.85:
            return (best_user_id, float(best_score))
        return None

if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv

    # Fix relative imports when running as a module directly
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    load_dotenv()
    default_db_path = os.getenv("DB_PATH", "./database/jarvis.db")

    def print_emitter(data):
        if data.get("status") == "confirmed":
            print(f"\nMatch found! Welcome {data['user']['name']} (ID: {data['user']['id']})")
        elif data.get("status") == "scanning":
            print(f"Scanning... {data['progress']}% | Face detected: {data['face_detected']}")
        elif data.get("status") in ["timeout", "unknown", "error"]:
            print(f"\n{data['message']}")

    async def main():
        print("Starting Face Scanner... Please stand in front of the camera.")
        scanner = FaceScanner(db_path=default_db_path, websocket_emitter=print_emitter)
        await scanner.scan()

    asyncio.run(main())
