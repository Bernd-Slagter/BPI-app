# Application Tracking System (ATS)

A basic Django application for tracking job positions, candidates, and applications.

## Features

- **Jobs** – Create and manage open positions (title, department, location, status: Open / On Hold / Filled / Cancelled).
- **Candidates** – Store candidate info (name, email, phone, resume summary).
- **Applications** – Link candidates to jobs with status (Submitted, Screening, Interview, Offer, Hired, Rejected, Withdrawn).

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations:

   ```bash
   python manage.py migrate
   ```

4. Create a superuser (optional, for admin access):

   ```bash
   python manage.py createsuperuser
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

6. Open **http://127.0.0.1:8000/** for the dashboard, or **http://127.0.0.1:8000/admin/** to manage data.

## Project structure

- `config/` – Django project settings and root URLs.
- `ats/` – ATS app: models (Job, Candidate, Application), views, URLs, admin.
- `templates/` – Base template and ATS pages (dashboard, job list/detail, candidates, applications).

## Usage

- **Dashboard** – Overview with open jobs, recent applications, and counts.
- **Jobs** – List jobs by status; open a job to see its applications.
- **Candidates** – List all candidates and application counts.
- **Applications** – List all applications with optional status filter.
- **Admin** – Add/edit Jobs, Candidates, and Applications (and change application status).
