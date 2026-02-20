# PolicyAssist - Basic UI

**⚠️ Temporary UI - Replace with proper frontend framework**

This is a simple HTML/CSS/JS frontend for testing the PolicyAssist backend. It's designed to be easily replaced with React, Vue, Next.js, or any other framework.

## Structure

- `index.html` - Main HTML structure
- `styles.css` - Basic styling
- `app.js` - API calls and form handling

## Usage

1. **Start the backend** (from `backend/`):
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Open `index.html`** in a browser or serve it:
   ```bash
   # Option 1: Open directly (may have CORS issues)
   # Option 2: Use a simple server
   python -m http.server 8080
   # Then visit http://localhost:8080
   ```

3. **Or serve with FastAPI static files** (add to `backend/app/main.py`):
   ```python
   from fastapi.staticfiles import StaticFiles
   app.mount("/ui", StaticFiles(directory="../frontend", html=True), name="ui")
   ```
   Then visit `http://127.0.0.1:8000/ui`

## API Configuration

Edit `app.js` and change `API_BASE` if your backend runs on a different port or host.

## Replacing This UI

When building the proper frontend:
1. Keep the same API endpoints (`/upload`, `/ask`, `/summarize`)
2. Update `API_BASE` to match your backend URL
3. Replace this entire `frontend/` directory with your framework's build output
