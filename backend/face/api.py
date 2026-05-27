import os
import sqlite3
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.face.scanner import FaceScanner
from backend.face.register import register_new_user

router = APIRouter(prefix="/face")

# Resolve database path
DB_PATH = os.getenv("DB_PATH", "./database/jarvis.db")

class RegisterRequest(BaseModel):
    name: str
    role: str
    language_pref: str

# WebSocket connection manager to stream events globally if needed
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/scan/stream")
async def websocket_stream(websocket: WebSocket):
    """
    Optional stream endpoint that keeps a client connection open 
    to listen to background scanning updates.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.websocket("/scan")
async def websocket_scan_direct(websocket: WebSocket):
    """
    Direct WebSocket connection that executes the face scanner on connect, 
    streaming real-time progress events directly to the caller, and closes on completion.
    """
    await websocket.accept()
    
    async def ws_emitter(data):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    scanner = FaceScanner(db_path=DB_PATH, websocket_emitter=ws_emitter)
    result = await scanner.scan()
    
    try:
        await websocket.send_json({"status": "completed", "result": result})
        await websocket.close()
    except Exception:
        pass

@router.post("/scan")
async def post_scan():
    """
    Triggers face scanner and broadcasts the scanning progress events 
    to any active WebSocket listeners (on /scan/stream), returning the final result.
    """
    scanner = FaceScanner(db_path=DB_PATH, websocket_emitter=manager.broadcast)
    result = await scanner.scan()
    return {"result": result}

@router.post("/register")
async def post_register(req: RegisterRequest):
    """
    Registers a new user profile and captures face embeddings via camera.
    """
    try:
        # Run blocking registration camera capture in a thread pool
        user_id = await asyncio.to_thread(
            register_new_user, req.name, req.role, req.language_pref, DB_PATH
        )
        return {"user_id": user_id, "success": True}
    except Exception as e:
        return {"user_id": None, "success": False, "error": str(e)}

@router.get("/users")
async def get_face_users(user_id: Optional[str] = Header(None)):
    """
    Admin only (checks user_id == 1 in header).
    Returns all users who have face_registered = True (or 1).
    """
    if user_id != "1":
        raise HTTPException(status_code=403, detail="Admin only access")
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE face_registered = 1")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

@router.delete("/user/{target_user_id}")
async def delete_face_user(target_user_id: int, user_id: Optional[str] = Header(None)):
    """
    Admin only (checks user_id == 1 in header).
    Deletes the user and all their face_embeddings rows.
    """
    if user_id != "1":
        raise HTTPException(status_code=403, detail="Admin only access")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Delete dependent embeddings first
    cursor.execute("DELETE FROM face_embeddings WHERE user_id = ?", (target_user_id,))
    # Delete user profile
    cursor.execute("DELETE FROM users WHERE id = ?", (target_user_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"User {target_user_id} and their embeddings deleted."}
