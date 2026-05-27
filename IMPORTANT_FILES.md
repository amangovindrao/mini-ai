# JARVIS-AI — Important Setup Notes

This project uses several local/generated files and folders that are intentionally NOT uploaded to GitHub.

These files are auto-generated, system-specific, very large, or contain sensitive/local runtime data.

---

# Ignored Files & Folders

The following are excluded using `.gitignore`.

## Python Virtual Environment

```text
venv/
```

Contains:
- installed Python packages
- local Python binaries
- environment-specific dependencies

Recreate using:

```bash
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Frontend Dependencies

```text
node_modules/
```

Contains:
- downloaded npm packages

Recreate using:

```bash
npm install
```

inside:

```text
frontend/
```

---

## Environment Variables

```text
.env
```

Contains:
- local configuration
- ports
- API URLs
- private settings

Create manually based on project requirements.

---

## SQLite Database

```text
database/jarvis.db
```

Contains:
- local runtime data
- users
- conversations
- AI memory

Auto-created using:

```bash
python database/db_init.py
```

---

## ChromaDB Memory Storage

```text
database/chroma/
```

Contains:
- vector embeddings
- semantic memory cache

Auto-created during database initialization.

---

## AI Models

```text
models/
```

Contains:
- Whisper models
- TTS models
- custom voice models
- future AI model checkpoints

These are intentionally excluded because model files are extremely large.

---

## Temporary Runtime Files

```text
temp/
```

Contains:
- temporary audio
- generated wav files
- cache data
- runtime temporary files

Auto-generated while running JARVIS.

---

# Required Setup Steps After Cloning

## 1. Create Python venv

```bash
py -3.11 -m venv venv
```

Activate:

```bash
venv\Scripts\activate
```

---

## 2. Install Python Packages

```bash
pip install -r requirements.txt
```

---

## 3. Install Frontend Packages

Inside frontend folder:

```bash
npm install
```

---

## 4. Initialize Database

```bash
python database/db_init.py
```

This creates:
- jarvis.db
- ChromaDB storage
- required tables

---

## 5. Install Ollama

Download from:
https://ollama.com

Then run:

```bash
ollama pull llama3.1:8b
```

---

# Notes

- Python version recommended: 3.11
- GPU support is optional
- CPU mode works completely fine
- Whisper + TTS models download automatically on first use

---

# GitHub Safety

The following are intentionally NOT uploaded:
- venv
- node_modules
- AI models
- databases
- cache files
- environment secrets

This keeps the repository:
- lightweight
- portable
- secure
- easy to clone