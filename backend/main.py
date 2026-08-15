import os
import re
import json
import requests as http_requests
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
from groq import Groq

app = FastAPI(title="AI Study Planner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Config — read from environment
# ---------------------------------------------------------------------------
GROQ_API_KEY          = os.environ.get("GROQ_API_KEY", "")
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL", "").rstrip("/")

# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------
def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages_text.append(f"[Page {page_num + 1}]\n{text}")
    doc.close()
    full_text = "\n\n".join(pages_text)
    # Keep within LLM context window (~30k chars)
    return full_text[:30000]


# ---------------------------------------------------------------------------
# Route 1: Cloudflare Worker (preferred when CLOUDFLARE_WORKER_URL is set)
# ---------------------------------------------------------------------------
def call_cloudflare_worker(
    pdf_text: str,
    manual_topics: str,
    num_days: int,
    hours_per_day: float,
    subject_name: str,
) -> List[dict]:
    """Forward the request to the Cloudflare AI Worker."""
    payload = {
        "pdf_text": pdf_text,
        "manual_topics": manual_topics,
        "num_days": num_days,
        "hours_per_day": hours_per_day,
        "subject_name": subject_name,
    }
    try:
        resp = http_requests.post(
            CLOUDFLARE_WORKER_URL,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise ValueError(data.get("error", "Worker returned failure"))
        return data["plan"]
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Cloudflare Worker timed out.")
    except http_requests.exceptions.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cloudflare Worker HTTP error: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cloudflare Worker error: {exc}",
        )


# ---------------------------------------------------------------------------
# Route 2: Groq API fallback
# ---------------------------------------------------------------------------
def call_groq(
    pdf_text: str,
    manual_topics: str,
    num_days: int,
    hours_per_day: float,
    subject_name: str,
) -> List[dict]:
    """Call Groq LLM (llama-3.3-70b-versatile) to produce a study plan."""
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=(
                "No LLM configured. Set CLOUDFLARE_WORKER_URL (Cloudflare Worker) "
                "or GROQ_API_KEY (Groq fallback) as environment variables."
            ),
        )

    client = Groq(api_key=GROQ_API_KEY)

    context_parts = []
    if pdf_text.strip():
        context_parts.append(f"=== SYLLABUS / PDF CONTENT ===\n{pdf_text.strip()}")
    if manual_topics.strip():
        context_parts.append(
            f"=== ADDITIONAL TOPICS MENTIONED BY STUDENT ===\n{manual_topics.strip()}"
        )
    context_block = "\n\n".join(context_parts) if context_parts else "No content provided."

    system_prompt = (
        "You are an expert educational study planner. "
        "Analyse the provided syllabus / PDF content and create "
        "a highly detailed, realistic, day-by-day study plan that maps exactly to "
        "the content. Always respond with valid JSON only — no markdown fences, "
        "no commentary, no trailing text."
    )

    user_prompt = f"""Subject / Course Name: {subject_name if subject_name else 'General Study'}
Total Study Days: {num_days}
Hours Available Per Day: {hours_per_day}

{context_block}

---

Create a JSON ARRAY of exactly {num_days} day-plan objects. Each object must have:
  "day"                : integer (1 to {num_days})
  "topic"              : string — the main topic for this day (must directly match content above)
  "subtopics"          : array of 2-5 strings — specific subtopics/sections to cover
  "reading"            : string — exact chapter / section / page references from the content (be precise)
  "tasks"              : array of 3-5 actionable task strings (e.g. "Read Section 2.3", "Solve 10 practice questions")
  "key_concepts"       : array of 3-6 important terms or concepts the student must understand today
  "estimated_duration" : string — total study time today (e.g. "3.5 hours")
  "difficulty"         : string — one of "Beginner", "Intermediate", "Advanced"
  "tips"               : string — one concise study tip for this day

Important rules:
- Distribute the content evenly across all {num_days} days.
- Earlier days should cover foundational/introductory material; later days go deeper.
- Each day must reference REAL content from the provided text, not generic filler.
- Return ONLY a raw JSON array starting with [ and ending with ]. No other text.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.25,
        max_tokens=8000,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Main plan generator — tries Worker first, falls back to Groq
# ---------------------------------------------------------------------------
def generate_plan_via_llm(
    pdf_text: str,
    manual_topics: str,
    num_days: int,
    hours_per_day: float,
    subject_name: str,
) -> tuple[List[dict], str]:
    """
    Returns (plan, provider_used).
    Prefers Cloudflare Worker if CLOUDFLARE_WORKER_URL is configured,
    otherwise falls back to Groq.
    """
    if CLOUDFLARE_WORKER_URL:
        plan = call_cloudflare_worker(
            pdf_text, manual_topics, num_days, hours_per_day, subject_name
        )
        return plan, "Cloudflare Workers AI"
    else:
        plan = call_groq(
            pdf_text, manual_topics, num_days, hours_per_day, subject_name
        )
        return plan, "Groq (llama-3.3-70b-versatile)"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    provider = "Cloudflare Workers AI" if CLOUDFLARE_WORKER_URL else "Groq"
    return {
        "status": "ok",
        "service": "AI Study Planner API",
        "llm_provider": provider,
        "cloudflare_worker_configured": bool(CLOUDFLARE_WORKER_URL),
        "groq_configured": bool(GROQ_API_KEY),
    }


@app.post("/generate-plan")
async def generate_plan(
    num_days: int = Form(30),
    hours_per_day: float = Form(4.0),
    subject_name: str = Form(""),
    manual_topics: str = Form(""),
    pdf_file: Optional[UploadFile] = File(None),
):
    """
    Generate a day-by-day study plan from an uploaded PDF and/or manual topics.
    Uses Cloudflare Worker if CLOUDFLARE_WORKER_URL is set, otherwise Groq.
    """
    # ── PDF extraction ────────────────────────────────────────────────────
    pdf_text = ""
    if pdf_file and pdf_file.filename:
        contents = await pdf_file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")
        try:
            pdf_text = extract_pdf_text(contents)
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Could not parse PDF: {exc}"
            )

    # ── Validation ────────────────────────────────────────────────────────
    if not pdf_text.strip() and not manual_topics.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a PDF file, manual topics, or both.",
        )
    if num_days < 1 or num_days > 365:
        raise HTTPException(
            status_code=400, detail="num_days must be between 1 and 365."
        )
    if hours_per_day <= 0 or hours_per_day > 24:
        raise HTTPException(
            status_code=400, detail="hours_per_day must be between 0.5 and 24."
        )

    # ── Generate ──────────────────────────────────────────────────────────
    try:
        plan, provider = generate_plan_via_llm(
            pdf_text=pdf_text,
            manual_topics=manual_topics,
            num_days=num_days,
            hours_per_day=hours_per_day,
            subject_name=subject_name,
        )
    except HTTPException:
        raise
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"LLM returned malformed JSON. Try again. ({exc})",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Plan generation failed: {exc}",
        )

    return {
        "success": True,
        "subject": subject_name,
        "total_days": len(plan),
        "hours_per_day": hours_per_day,
        "llm_provider": provider,
        "plan": plan,
    }
