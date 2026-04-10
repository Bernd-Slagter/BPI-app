# ATS — AI-Powered Applicant Tracking System

A Django-based Applicant Tracking System built for a BPI academic assignment. The system replaces manual recruiter steps with AI (Claude) at every stage of the hiring pipeline.

## Features

- **Job management** — post positions with employment type, salary range, and deadline; AI-enhance descriptions; parse job files (PDF, Word, Outlook email)
- **Candidate management** — track candidates with source, LinkedIn, and resume; AI auto-parses uploaded resumes
- **Application pipeline** — Submitted → Screening → Interview → Offer → Hired with stage-specific fields (interview date, offer amount)
- **AI screening** — automatic match scoring (0–100) and Advance/Hold/Reject recommendation on every application
- **AI interview guide** — generates tailored interview questions when an application reaches the Interview stage
- **AI matching** — rank all candidates against a job, or all open jobs against a candidate
- **Login required** — all pages protected; Django admin at `/admin/`

## Tech stack

- Python 3.12, Django 5.x
- Anthropic Claude API (`claude-haiku` for fast scoring, `claude-sonnet` for rich generation)
- SQLite (dev) / volume-mounted SQLite (Docker)
- Gunicorn + Docker for deployment
- Tailscale-friendly (binds to any interface)

## Quick start (local)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env with your API key
echo ANTHROPIC_API_KEY=sk-ant-... > .env

# 4. Run migrations and create an admin account
python manage.py migrate
python manage.py createsuperuser

# 5. Start the dev server
python manage.py runserver
```

Open http://localhost:8000

## Docker

```bash
# Edit docker-compose.yml — set DJANGO_SUPERUSER_PASSWORD and ANTHROPIC_API_KEY
docker compose up --build
```

The database and uploaded files are stored in named Docker volumes and survive rebuilds.

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | *(none — AI features disabled)* |
| `DJANGO_SECRET_KEY` | Django secret key | dev key |
| `DJANGO_DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DATABASE_PATH` | Path to SQLite file | `db.sqlite3` next to `manage.py` |
| `DJANGO_SUPERUSER_USERNAME` | Auto-created admin username (Docker) | — |
| `DJANGO_SUPERUSER_PASSWORD` | Auto-created admin password (Docker) | — |
