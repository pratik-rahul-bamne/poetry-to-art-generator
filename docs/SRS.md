# Software Requirements Specification (SRS)
## AI Poem Visualizer — v2.0

**Document Version:** 2.0  
**Date:** June 2026  
**Authors:** Development Team

---

## 1. Introduction

### 1.1 Purpose
This SRS defines the functional and non-functional requirements for the AI Poem Visualizer — a web application that transforms user-submitted poems into AI-generated visual artwork.

### 1.2 Scope
The system accepts poems in English, Hindi, and Marathi; performs NLP analysis; generates matching background images via AI; composes typography-overlaid final artwork; and provides downloadable output in multiple formats.

### 1.3 Definitions
| Term | Definition |
|------|------------|
| NLP | Natural Language Processing |
| SD | Stable Diffusion (local image generation model) |
| JWT | JSON Web Token (stateless authentication) |
| Provider | An AI backend (Gemini, Pollinations, SD) |

---

## 2. System Overview

```
User → Frontend SPA → FastAPI Backend → AI Provider Layer → Output Images
                                      ↓
                               SQLite/PostgreSQL DB
                               (users, poems, generations, downloads, logs)
```

---

## 3. Functional Requirements

### 3.1 Guest Users
- FR-G-01: Submit a poem (max 1200 characters) in English, Hindi, or Marathi
- FR-G-02: Select theme override (romantic, nature, dark, joyful, mystical, melancholic)
- FR-G-03: Select output format (1:1 square, 9:16 story)
- FR-G-04: Select image provider (Stable Diffusion local, Pollinations cloud)
- FR-G-05: Configure SD parameters (style, size, steps, guidance, seed)
- FR-G-06: View generated artwork in preview
- FR-G-07: Download artwork as PNG
- FR-G-08: View public gallery of recent creations

### 3.2 Registered Users
- FR-U-01: Register with name, email, password
- FR-U-02: Login with email, password; receive JWT
- FR-U-03: Logout (client-side token discard)
- FR-U-04: View and update display name
- FR-U-05: Save poems to personal collection
- FR-U-06: View saved poems, generate from saved, delete saved
- FR-U-07: View personal generation history with status and timing

### 3.3 Admin Users
- FR-A-01: View system-wide stats (users, poems, generations, downloads)
- FR-A-02: List all registered users with roles and status
- FR-A-03: View recent activity logs

### 3.4 AI Pipeline
- FR-P-01: Analyze poem → extract theme, mood, visual_prompt, language
- FR-P-02: Generate background image from visual_prompt
- FR-P-03: Compose final artwork (overlay poem text on background)
- FR-P-04: Support provider chain with automatic fallback
- FR-P-05: Log every AI provider call (timing, tokens, status)

---

## 4. Non-Functional Requirements

### 4.1 Performance
- NFR-01: Pollinations image generation < 15 seconds
- NFR-02: Gemini NLP analysis < 5 seconds
- NFR-03: Image composition < 3 seconds
- NFR-04: API response time < 200ms for non-AI endpoints

### 4.2 Security
- NFR-05: Passwords hashed with bcrypt (cost factor ≥ 12)
- NFR-06: JWT tokens signed with HS256
- NFR-07: SQL injection protection via SQLAlchemy ORM
- NFR-08: XSS protection via HTML escaping in frontend
- NFR-09: Rate limiting: 10 req/hr guests, 50 req/hr registered
- NFR-10: CORS restricted in production

### 4.3 Reliability
- NFR-11: AI provider chain with automatic fallback
- NFR-12: All database writes wrapped in transactions
- NFR-13: Graceful error handling with user-friendly messages

### 4.4 Scalability
- NFR-14: Database swappable from SQLite to PostgreSQL via DATABASE_URL
- NFR-15: AI provider abstraction allows adding new providers without code changes in routes
- NFR-16: Rate limiting store swappable from in-memory to Redis

---

## 5. Constraints
- Python 3.10+ required
- Stable Diffusion local mode requires ~4GB RAM
- No GPU required (CPU-only mode supported)
- Free tier: Gemini Flash API limits apply
