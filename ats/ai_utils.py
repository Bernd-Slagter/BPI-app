"""
AI utility functions for the ATS.
All functions degrade gracefully when ANTHROPIC_API_KEY is not set or the
anthropic package is not installed — they return safe defaults so existing
CRUD operations are never broken.
"""
import base64
import email as email_lib
import io
import json
import logging
import os
import re
import zipfile

from django.conf import settings

logger = logging.getLogger(__name__)

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"


def _get_client():
    """Return an Anthropic client, or None if key / package is unavailable."""
    try:
        import anthropic  # noqa: PLC0415
        key = getattr(settings, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            logger.debug("ANTHROPIC_API_KEY not set — AI features disabled")
            return None
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        logger.warning("anthropic package not installed — AI features disabled")
        return None


# ---------------------------------------------------------------------------
# File text extraction
# ---------------------------------------------------------------------------

def _extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from a file, handling common document formats.
    Returns an empty string if extraction fails.
    """
    name = filename.lower()

    if name.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                with z.open("word/document.xml") as f:
                    xml = f.read().decode("utf-8", errors="replace")
            text = re.sub(r"<[^>]+>", " ", xml)
            return re.sub(r"\s+", " ", text).strip()
        except Exception:
            pass

    if name.endswith(".msg"):
        try:
            import extract_msg  # noqa: PLC0415
            msg = extract_msg.openMsg(io.BytesIO(file_bytes))
            parts = [msg.subject or "", msg.body or ""]
            return "\n".join(p for p in parts if p).strip()
        except Exception:
            pass

    if name.endswith(".eml"):
        try:
            msg = email_lib.message_from_bytes(file_bytes)
            parts = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            parts.append(payload.decode("utf-8", errors="replace"))
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode("utf-8", errors="replace"))
            return "\n".join(parts).strip()
        except Exception:
            pass

    # Default: UTF-8 decode (covers .txt, .rtf, .md, .csv, .doc, etc.)
    return file_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 1. Resume parsing
# ---------------------------------------------------------------------------

def parse_resume(file_path: str, existing_summary: str = "") -> str:
    """
    Extract a concise candidate summary from a resume file.

    Supports PDF (via Anthropic document vision) and plain-text files.
    Returns the existing_summary unchanged if AI is unavailable or fails.
    """
    client = _get_client()
    if not client:
        return existing_summary

    try:
        import anthropic  # noqa: PLC0415

        file_path = str(file_path)
        with open(file_path, "rb") as fh:
            raw = fh.read()

        fname = os.path.basename(file_path).lower()
        instruction = (
            "You are an HR assistant. Extract structured candidate information "
            "from this resume. Return a concise plain-text summary (max 200 words) "
            "covering: key skills, years of experience, most recent roles, and "
            "highest education level. Do not include personal contact details."
        )

        if fname.endswith(".pdf"):
            content = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.standard_b64encode(raw).decode("utf-8"),
                    },
                },
                {"type": "text", "text": instruction},
            ]
        else:
            text_content = _extract_text(raw, fname)
            content = f"{instruction}\n\nRESUME:\n{text_content}"

        response = client.messages.create(
            model=HAIKU,
            max_tokens=400,
            timeout=30,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.warning("parse_resume failed: %s", exc)
        return existing_summary


# ---------------------------------------------------------------------------
# 2. Job file parsing
# ---------------------------------------------------------------------------

def parse_job_file(file_bytes: bytes, filename: str) -> dict:
    """
    Extract job details from an uploaded document (PDF or plain text).
    Returns {"title": str, "department": str, "location": str, "description": str}.
    All keys are always present; values may be empty strings if not found.
    """
    default = {"title": "", "department": "", "location": "", "description": ""}
    client = _get_client()
    if not client:
        return default

    try:
        instruction = (
            "You are an HR assistant. The input may be a formal job posting, an informal "
            "request from a manager, a forwarded email, or any other message about a hiring need. "
            "Your job is to interpret the intent and produce structured vacancy data.\n\n"
            "Rules:\n"
            "- title: infer a concise job title even if not explicitly stated "
            "(e.g. 'we need someone for backend' → 'Backend Developer')\n"
            "- department: infer from context if possible (e.g. 'engineering team', 'finance dept')\n"
            "- location: extract if mentioned, otherwise leave empty\n"
            "- description: write a clean, professional description based on ALL information "
            "in the message — skills mentioned, responsibilities implied, team context, "
            "urgency, and any other relevant details. Expand bullet points into prose where helpful.\n\n"
            "Respond ONLY with a JSON object — no markdown, no extra text:\n"
            '{"title": "...", "department": "...", "location": "...", "description": "..."}\n\n'
            "Never leave title empty — always infer something reasonable."
        )

        if filename.lower().endswith(".pdf"):
            content = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.standard_b64encode(file_bytes).decode("utf-8"),
                    },
                },
                {"type": "text", "text": instruction},
            ]
        else:
            text_content = _extract_text(file_bytes, filename)
            content = f"{instruction}\n\nDOCUMENT:\n{text_content}"

        response = client.messages.create(
            model=HAIKU,
            max_tokens=800,
            timeout=30,
            messages=[{"role": "user", "content": content}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "title": str(data.get("title", "")),
            "department": str(data.get("department", "")),
            "location": str(data.get("location", "")),
            "description": str(data.get("description", "")),
        }
    except Exception as exc:
        logger.warning("parse_job_file failed: %s", exc)
        return default


# ---------------------------------------------------------------------------
# 3. Job description enhancement
# ---------------------------------------------------------------------------

def enhance_job_description(title: str, department: str, existing_description: str) -> str:
    """
    Return a professionally written job description.
    The caller is responsible for showing it to the human for review — this
    function never saves to the database.
    """
    client = _get_client()
    if not client:
        return existing_description

    try:
        prompt = (
            f"You are a technical recruiter. Write a professional job description for "
            f"the role '{title}' in the '{department}' department.\n\n"
            f"Draft provided by the user:\n{existing_description or '(none)'}\n\n"
            "Structure your response as plain text with these sections:\n"
            "Role Summary (2 sentences)\n"
            "Key Responsibilities (5 bullet points)\n"
            "Required Qualifications (4-5 bullet points)\n"
            "Nice-to-Have Skills (2-3 bullet points)\n\n"
            "Return only the job description text, no extra commentary."
        )
        response = _get_client().messages.create(
            model=SONNET,
            max_tokens=800,
            timeout=30,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.warning("enhance_job_description failed: %s", exc)
        return existing_description


# ---------------------------------------------------------------------------
# 4. Candidate-job match scoring
# ---------------------------------------------------------------------------

def score_candidate_job_match(
    resume_summary: str, job_title: str, job_description: str
) -> dict:
    """
    Score how well a candidate matches a job on a 0-100 scale.
    Returns {"score": int|None, "rationale": str}.
    """
    default = {"score": None, "rationale": ""}
    client = _get_client()
    if not client:
        return default

    try:
        prompt = (
            "Score how well this candidate matches this job on a scale of 0 to 100. "
            "Respond ONLY with a JSON object in this exact format — no markdown, no extra text:\n"
            '{"score": <integer 0-100>, "rationale": "<one concise paragraph>"}\n\n'
            f"Candidate summary:\n{resume_summary or '(no summary provided)'}\n\n"
            f"Job title: {job_title}\n"
            f"Job description:\n{job_description or '(no description provided)'}"
        )
        response = client.messages.create(
            model=HAIKU,
            max_tokens=300,
            timeout=30,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "score": int(data.get("score", 0)),
            "rationale": str(data.get("rationale", "")),
        }
    except Exception as exc:
        logger.warning("score_candidate_job_match failed: %s", exc)
        return default


# ---------------------------------------------------------------------------
# 5. Application screening
# ---------------------------------------------------------------------------

def screen_application(
    resume_summary: str, job_title: str, job_description: str, notes: str = ""
) -> dict:
    """
    Screen an application and recommend advance / hold / reject.
    Returns {"recommendation": str, "reasoning": str}.
    """
    default = {"recommendation": "", "reasoning": ""}
    client = _get_client()
    if not client:
        return default

    try:
        prompt = (
            "You are an ATS screening assistant. Review this job application and respond "
            "ONLY with a JSON object — no markdown, no extra text:\n"
            '{"recommendation": "advance|hold|reject", "reasoning": "<one concise paragraph>"}\n\n'
            f"Candidate summary:\n{resume_summary or '(no summary provided)'}\n\n"
            f"Job title: {job_title}\n"
            f"Job description:\n{job_description or '(no description provided)'}\n\n"
            f"Recruiter notes:\n{notes or '(none)'}"
        )
        response = client.messages.create(
            model=HAIKU,
            max_tokens=300,
            timeout=30,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        rec = str(data.get("recommendation", "")).lower()
        if rec not in ("advance", "hold", "reject"):
            rec = "hold"
        return {"recommendation": rec, "reasoning": str(data.get("reasoning", ""))}
    except Exception as exc:
        logger.warning("screen_application failed: %s", exc)
        return default


# ---------------------------------------------------------------------------
# 6. Interview question generation
# ---------------------------------------------------------------------------

def generate_interview_questions(
    resume_summary: str, job_title: str, job_description: str
) -> str:
    """
    Generate a structured interview guide for a candidate/role combination.
    Returns a plain-text (Markdown) string.
    """
    client = _get_client()
    if not client:
        return ""

    try:
        prompt = (
            "You are an experienced hiring manager. Generate a structured interview guide "
            f"for the role '{job_title}'.\n\n"
            f"Candidate summary:\n{resume_summary or '(no summary provided)'}\n\n"
            f"Job description:\n{job_description or '(no description provided)'}\n\n"
            "Include:\n"
            "- 3 role-specific technical questions\n"
            "- 2 behavioural questions (STAR framework)\n"
            "- 1 culture-fit question\n"
            "- 1 question about a potential gap or concern in the candidate's background\n\n"
            "For each question add a brief note on what a strong answer looks like. "
            "Format as a numbered Markdown list."
        )
        response = client.messages.create(
            model=SONNET,
            max_tokens=1000,
            timeout=45,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.warning("generate_interview_questions failed: %s", exc)
        return ""
