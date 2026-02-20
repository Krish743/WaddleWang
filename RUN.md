# How to Run PolicyAssist

## Prerequisites

- Python 3.11+ installed
- Groq API key (get from https://console.groq.com/) OR OpenAI API key

## Quick Run (5 steps)

```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate venv
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1    # Windows PowerShell
# OR: source .venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure .env
copy .env.example .env
# Edit .env and add your API_KEY

# 5. Run
uvicorn app.main:app --reload
```

## Access Points

- **UI:** http://127.0.0.1:8000/ui
- **API Docs:** http://127.0.0.1:8000/docs
- **Health:** http://127.0.0.1:8000/health

## Troubleshooting

**"Module not found" errors:**
- Make sure venv is activated (you should see `(.venv)` in prompt)
- Run `pip install -r requirements.txt` again

**"API key" errors:**
- Check that `backend/.env` exists (not root `.env`)
- Verify `API_KEY=...` is set correctly in `backend/.env`

**Port already in use:**
- Change port: `uvicorn app.main:app --reload --port 8001`
