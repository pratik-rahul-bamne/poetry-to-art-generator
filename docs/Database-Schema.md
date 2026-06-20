# Database Schema
## AI Poem Visualizer — v2.0

---

## Overview

The application uses **SQLite** in development and is swappable to **PostgreSQL** via `DATABASE_URL` environment variable. All tables use **UUID primary keys** (stored as VARCHAR(36) in SQLite).

---

## Entity Relationship Diagram

```
users
 └──< poems (user_id → users.id)
         └──< generations (poem_id → poems.id)
                   └──< downloads (generation_id → generations.id)

users ──< activity_logs (user_id → users.id)

ai_provider_logs (standalone — no FK to users)
```

---

## Table: `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PK | UUID v4 |
| name | VARCHAR(100) | NOT NULL | Display name |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Login identifier |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hash |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'user' | 'user' or 'admin' |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 'active', 'suspended', 'deleted' |
| created_at | DATETIME | NOT NULL | UTC timestamp |
| updated_at | DATETIME | NOT NULL | Auto-updated on change |
| last_login | DATETIME | NULLABLE | Updated on each login |

---

## Table: `poems`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PK | UUID v4 |
| user_id | VARCHAR(36) | FK → users.id, NULLABLE, INDEX | NULL for guest submissions |
| title | VARCHAR(255) | NULLABLE | Optional user-provided title |
| poem_text | TEXT | NOT NULL | Full poem content |
| language | VARCHAR(50) | NULLABLE | Detected: 'English', 'Hindi/Marathi' |
| theme | VARCHAR(100) | NULLABLE | AI-extracted theme |
| mood | VARCHAR(100) | NULLABLE | AI-extracted mood |
| created_at | DATETIME | NOT NULL | UTC timestamp |
| updated_at | DATETIME | NOT NULL | Auto-updated on change |

---

## Table: `generations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PK | UUID v4 |
| poem_id | VARCHAR(36) | FK → poems.id, NULLABLE, INDEX | Links artwork to poem |
| image_prompt | TEXT | NULLABLE | AI-generated visual prompt |
| provider_used | VARCHAR(100) | NULLABLE | 'pollinations', 'gemini', 'stable-diffusion' |
| image_url | VARCHAR(500) | NULLABLE | Path to background image |
| final_artwork_url | VARCHAR(500) | NULLABLE | Path to composed final image |
| generation_time | FLOAT | NULLABLE | Total seconds for composition |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 'pending', 'completed', 'failed' |
| created_at | DATETIME | NOT NULL | UTC timestamp |

---

## Table: `downloads`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PK | UUID v4 |
| generation_id | VARCHAR(36) | FK → generations.id, NULLABLE, INDEX | Which artwork was downloaded |
| downloaded_at | DATETIME | NOT NULL | UTC timestamp |
| ip_address | VARCHAR(45) | NULLABLE | Client IP (IPv4 or IPv6) |
| device_info | VARCHAR(500) | NULLABLE | User-agent string |

---

## Table: `activity_logs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PK | UUID v4 |
| user_id | VARCHAR(36) | FK → users.id, NULLABLE, INDEX | NULL for guest actions |
| action | VARCHAR(100) | NOT NULL | e.g. 'login', 'register', 'generate' |
| module | VARCHAR(100) | NOT NULL | e.g. 'auth', 'generation', 'poem' |
| description | TEXT | NULLABLE | Human-readable detail |
| created_at | DATETIME | NOT NULL, INDEX | UTC timestamp |

---

## Table: `ai_provider_logs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PK | UUID v4 |
| provider_name | VARCHAR(100) | NOT NULL, INDEX | 'gemini', 'pollinations', 'stable-diffusion' |
| operation | VARCHAR(100) | NOT NULL | 'analyze' or 'generate_image' |
| tokens_used | INTEGER | NULLABLE | LLM token count (where available) |
| request_time | DATETIME | NULLABLE | When request was sent |
| response_time | FLOAT | NULLABLE | Seconds to receive response |
| cost_usd | FLOAT | NULLABLE | Estimated cost in USD |
| status | VARCHAR(20) | NOT NULL | 'success', 'error', 'timeout' |
| error_message | VARCHAR(500) | NULLABLE | Error detail on failure |
| created_at | DATETIME | NOT NULL, INDEX | UTC timestamp |

---

## Migration Strategy

1. **Current**: Auto-created tables via `Base.metadata.create_all()` on startup
2. **Future**: Alembic migrations when schema changes are needed
   ```bash
   alembic init alembic
   alembic revision --autogenerate -m "initial_schema"
   alembic upgrade head
   ```
3. **To switch to PostgreSQL**: Change `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/poem_visualizer
   ```
