# Deployment Guide
## AI Poem Visualizer v2.0

---

## Local Development

### Prerequisites
- Python 3.10+
- pip

### Setup
```bash
# 1. Clone / navigate to project
cd "Poetry to Art Generator"

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download fonts
python -m backend.utils.font_downloader

# 5. Configure environment
copy .env.example .env  # Windows
# Edit .env and add your GEMINI_API_KEY

# 6. Run server
uvicorn backend.app.main:app --reload --port 8000

# 7. Open browser
# http://localhost:8000
```

### Environment Variables (.env)
```env
GEMINI_API_KEY=your_gemini_key_here
NLP_PROVIDER=gemini
IMAGE_PROVIDER=pollinations
SECRET_KEY=change-me-in-production-use-a-long-random-string
```

---

## Production Deployment (Render)

1. Push to GitHub
2. Create a **Web Service** on [render.com](https://render.com)
3. Build command:
   ```
   pip install -r requirements.txt && python -m backend.utils.font_downloader
   ```
4. Start command:
   ```
   uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
   ```
5. Add environment variables in Render dashboard:
   - `GEMINI_API_KEY`
   - `SECRET_KEY` (generate a secure random string)
   - `APP_ENV=production`
   - `ALLOWED_ORIGINS=https://your-domain.com`

---

## Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python -m backend.utils.font_downloader

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t poem-visualizer .
docker run -p 8000:8000 --env-file .env poem-visualizer
```

---

## Database

- **Development**: SQLite (auto-created at `poem_visualizer.db`)
- **Production**: Set `DATABASE_URL=postgresql://...` in environment
- Tables are auto-created on first startup via `init_db()`

---

## Switching to PostgreSQL

```env
DATABASE_URL=postgresql://username:password@localhost:5432/poem_visualizer
```

Install driver: `pip install psycopg2-binary`

---

## Creating First Admin User

After first startup, use the API to register, then manually update the role in SQLite:
```bash
sqlite3 poem_visualizer.db "UPDATE users SET role='admin' WHERE email='your@email.com';"
```
