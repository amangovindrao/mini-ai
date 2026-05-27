CREATE TABLE IF NOT EXISTS users (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   name TEXT NOT NULL,
   role TEXT CHECK(role IN ('admin', 'user', 'guest', 'child')) NOT NULL,
   language_pref TEXT DEFAULT 'hinglish',
   personality_style TEXT DEFAULT 'casual',
   energy_level TEXT DEFAULT 'medium',
   humor_type TEXT DEFAULT 'light',
   nickname TEXT,
   face_registered BOOLEAN DEFAULT 0,
   voice_registered BOOLEAN DEFAULT 0,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS face_embeddings (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   user_id INTEGER NOT NULL,
   embedding_blob BLOB,
   photo_path TEXT,
   confidence REAL,
   captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS conversations (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   user_id INTEGER NOT NULL,
   message TEXT,
   response TEXT,
   language TEXT,
   emotion TEXT,
   confidence_score REAL,
   processing_time_ms INTEGER,
   timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_memory (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   user_id INTEGER NOT NULL,
   memory_type TEXT,
   content TEXT,
   importance_score REAL DEFAULT 0.5,
   embedding_blob BLOB,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS personality_profiles (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   user_id INTEGER UNIQUE NOT NULL,
   tone TEXT,
   speed TEXT,
   slang_bank TEXT,
   references_json TEXT,
   filler_words TEXT,
   language_mix_ratio TEXT DEFAULT '60:40',
   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tasks (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   user_id INTEGER NOT NULL,
   title TEXT,
   description TEXT,
   status TEXT DEFAULT 'pending',
   priority TEXT DEFAULT 'medium',
   reminder_time TIMESTAMP,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS pending_learning (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   asked_by_user_id INTEGER NOT NULL,
   original_question TEXT,
   similar_questions_json TEXT,
   frequency_count INTEGER DEFAULT 1,
   first_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   last_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   status TEXT DEFAULT 'pending',
   FOREIGN KEY(asked_by_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS learned_responses (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   trigger_phrases_json TEXT,
   response_template TEXT,
   language TEXT DEFAULT 'hinglish',
   emotion_tone TEXT DEFAULT 'calm',
   code_function_name TEXT,
   code_file_path TEXT,
   created_by_admin INTEGER,
   is_active BOOLEAN DEFAULT 0,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   FOREIGN KEY(created_by_admin) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS code_sandbox (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   file_path TEXT UNIQUE,
   file_name TEXT,
   allowed_to_edit BOOLEAN DEFAULT 0,
   last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   modified_by TEXT,
   backup_path TEXT
);

CREATE TABLE IF NOT EXISTS admin_notifications (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   type TEXT,
   message TEXT,
   related_id INTEGER,
   is_read BOOLEAN DEFAULT 0,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
