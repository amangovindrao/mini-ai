import sqlite3
import os
import chromadb
from dotenv import load_dotenv

def init_db():
    # Load environment variables from .env
    load_dotenv()
    
    # Get paths from .env or use defaults
    db_path = os.getenv("DB_PATH", "./database/jarvis.db")
    schema_path = "./database/schema.sql"
    
    # Ensure database directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 1. Run schema.sql to create all 10 tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_script = f.read()
    
    cursor.executescript(schema_script)
    conn.commit()

    # 2. Insert the admin user if they do not exist
    cursor.execute("""
        INSERT INTO users (id, name, role, language_pref, personality_style) 
        SELECT 1, 'Yashit', 'admin', 'hinglish', 'casual'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = 1)
    """)
    conn.commit()

    # 3. Insert personality profile for Yashit
    cursor.execute("""
        INSERT INTO personality_profiles (user_id, tone, slang_bank)
        SELECT 1, 'casual', 'bhai,yaar,bro'
        WHERE NOT EXISTS (SELECT 1 FROM personality_profiles WHERE user_id = 1)
    """)
    conn.commit()

    # 4. Insert 4 rows into code_sandbox with allowed_to_edit=1
    sandbox_files = [
        "backend/responses/learned_responses.py",
        "backend/responses/hinglish_responses.py",
        "backend/responses/bhojpuri_responses.py",
        "backend/responses/emotion_responses.py"
    ]
    
    for file_path in sandbox_files:
        file_name = os.path.basename(file_path)
        cursor.execute("""
            INSERT INTO code_sandbox (file_path, file_name, allowed_to_edit)
            SELECT ?, ?, 1
            WHERE NOT EXISTS (SELECT 1 FROM code_sandbox WHERE file_path = ?)
        """, (file_path, file_name, file_path))
    conn.commit()
    conn.close()

    # 5. Initialize ChromaDB at the CHROMA_PATH from .env
    chroma_path = os.getenv("CHROMA_PATH", "./database/chroma")
    if chroma_path:
        os.makedirs(chroma_path, exist_ok=True)
        try:
            # PersistentClient is recommended in newer versions of chromadb
            chroma_client = chromadb.PersistentClient(path=chroma_path)
            # Creates collection named "user_1" for the admin
            chroma_client.get_or_create_collection(name="user_1")
        except Exception as e:
            print(f"Warning: Could not initialize ChromaDB: {e}")

    # 6. Print success message
    print("JARVIS Database initialized successfully")

if __name__ == "__main__":
    init_db()
