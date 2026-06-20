# API Documentation
## AI Poem Visualizer v2.0 — /api/v1/

**Base URL:** `http://localhost:8000/api/v1`  
**Interactive Docs:** `http://localhost:8000/api/docs` (Swagger UI)

---

## Authentication

Most endpoints are public. Protected endpoints require:
```
Authorization: Bearer <access_token>
```

Tokens are returned by register/login. They expire in 24 hours by default.

---

## 1. Authentication

### POST /auth/register
Create a new user account.

**Request:**
```json
{ "name": "Pratik Bamne", "email": "pratik@example.com", "password": "secure123" }
```

**Response 201:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "name": "Pratik Bamne",
  "email": "pratik@example.com",
  "role": "user"
}
```

**Errors:** 409 (email already exists), 422 (validation)

---

### POST /auth/login
Login and receive a JWT.

**Request:**
```json
{ "email": "pratik@example.com", "password": "secure123" }
```

**Response 200:** Same as register response.

**Errors:** 401 (invalid credentials), 403 (account suspended)

---

### POST /auth/logout
Invalidate session (client should discard token).

**Auth Required:** Yes  
**Response 200:** `{ "message": "Logged out successfully." }`

---

### GET /auth/me
Get current user profile.

**Auth Required:** Yes  
**Response 200:**
```json
{
  "id": "uuid",
  "name": "Pratik Bamne",
  "email": "pratik@example.com",
  "role": "user",
  "status": "active",
  "created_at": "2026-06-19T05:30:00Z",
  "last_login": "2026-06-19T11:00:00Z"
}
```

---

## 2. Generation Pipeline

### POST /analyze
Analyze a poem and extract visual metadata.

**Request:**
```json
{ "poem": "Roses bloom in morning dew...", "theme_override": null }
```

**Response 200:**
```json
{
  "theme": "Nature",
  "mood": "Peaceful and serene",
  "image_prompt": "A misty garden at sunrise with golden light filtering through rose blossoms, soft watercolor style",
  "language": "English"
}
```

---

### POST /generate-image
Generate a background image.

**Request:**
```json
{
  "image_prompt": "A misty garden at sunrise...",
  "provider": "pollinations",
  "sd_style": "watercolor",
  "sd_width": 512,
  "sd_height": 512,
  "sd_steps": 20,
  "sd_guidance": 7.5,
  "sd_seed": -1
}
```

**Response 200:**
```json
{ "bg_filename": "bg_a1b2c3d4.png" }
```

---

### POST /compose
Overlay poem text on background image.

**Request:**
```json
{
  "poem": "Roses bloom in morning dew...",
  "bg_filename": "bg_a1b2c3d4.png",
  "theme": "Nature",
  "mood": "Peaceful",
  "format": "square"
}
```

**Response 200:**
```json
{
  "final_filename": "final_e5f6g7h8.png",
  "url": "/outputs/final_e5f6g7h8.png"
}
```

---

### GET /download/{filename}
Download a generated image as an attachment.

**Response:** PNG file (Content-Disposition: attachment)

---

### GET /gallery?limit=12
Get recent completed artworks for the public gallery.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "image_path": "/outputs/final_abc.png",
    "theme": "Nature",
    "mood": "Peaceful",
    "poem_text": "Roses bloom...",
    "created_at": "2026-06-19T10:00:00Z"
  }
]
```

---

### GET /history?page=1&per_page=20
User's generation history.

**Auth Required:** Yes

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "final_artwork_url": "/outputs/final_abc.png",
      "provider_used": "pollinations",
      "generation_time": 4.2,
      "status": "completed",
      "created_at": "2026-06-19T10:00:00Z"
    }
  ],
  "total": 15,
  "page": 1
}
```

---

### GET /sd-status
Check Stable Diffusion model loading status.

**Response 200:**
```json
{
  "ready": false,
  "loading": false,
  "provider": "Stable Diffusion 1.5 (CPU)",
  "styles": ["none", "photorealistic", "anime", "oil_painting", ...]
}
```

---

### POST /sd-preload
Trigger SD model loading in background.

**Response 200:**
```json
{ "status": "started", "message": "Pipeline loading started in background..." }
```

---

## 3. Poems (Auth Required)

### POST /poems
Save a poem to user's collection.

**Request:**
```json
{
  "poem_text": "Roses bloom...",
  "title": "Morning Roses",
  "language": "English",
  "theme": "Nature",
  "mood": "Peaceful"
}
```

**Response 201:** Poem object with id, created_at.

---

### GET /poems?page=1&per_page=20
List user's saved poems.

**Response 200:**
```json
{
  "items": [{ "id": "uuid", "title": "...", "poem_text": "...", "created_at": "..." }],
  "total": 5
}
```

---

### DELETE /poems/{id}
Delete a saved poem (owner only).

**Response 204:** No content.

---

## 4. Users (Auth Required)

### GET /users/me
Get profile (same as /auth/me).

### PATCH /users/me
Update display name.

**Request:** `{ "name": "New Name" }`

---

## 5. Admin (Admin Role Required)

### GET /admin/stats
System statistics.

**Response 200:**
```json
{
  "total_users": 42,
  "active_users": 40,
  "total_poems": 156,
  "total_generations": 89,
  "total_downloads": 234,
  "provider_breakdown": { "pollinations": 60, "stable-diffusion": 29 }
}
```

---

### GET /admin/users?page=1&per_page=50
List all users.

---

### GET /admin/logs?limit=50
Recent activity logs.

---

## Error Response Format
All errors follow FastAPI's standard format:
```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (missing required fields) |
| 401 | Not authenticated |
| 403 | Forbidden (wrong role) |
| 404 | Resource not found |
| 409 | Conflict (duplicate email) |
| 422 | Validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
