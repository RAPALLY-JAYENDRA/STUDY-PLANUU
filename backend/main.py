import os
import re
import json
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
# Groq client
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


def get_groq_client() -> Groq:
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY environment variable is not set.",
        )
    return Groq(api_key=GROQ_API_KEY)


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
    # Keep within LLM context window (roughly 30k chars)
    return full_text[:30000]


# ---------------------------------------------------------------------------
# LLM-based study plan generation
# ---------------------------------------------------------------------------
def generate_study_plan_with_llm(
    pdf_text: str,
    manual_topics: str,
    num_days: int,
    hours_per_day: float,
    subject_name: str,
) -> List[dict]:
    """Call Groq LLM to produce a structured day-by-day study plan."""

    client = get_groq_client()

    context_parts = []
    if pdf_text.strip():
        context_parts.append(
            f"=== SYLLABUS / PDF CONTENT ===\n{pdf_text.strip()}"
        )
    if manual_topics.strip():
        context_parts.append(
            f"=== ADDITIONAL TOPICS MENTIONED BY STUDENT ===\n{manual_topics.strip()}"
        )

    context_block = "\n\n".join(context_parts) if context_parts else "No content provided."

    system_prompt = (
        "You are an expert educational study planner. "
        "Your job is to analyse the provided syllabus / PDF content and create "
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
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.25,
        max_tokens=8000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if model adds them
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    # Extract JSON array
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "AI Study Planner API"}


@app.post("/generate-plan")
async def generate_plan(
    num_days: int = Form(30),
    hours_per_day: float = Form(4.0),
    subject_name: str = Form(""),
    manual_topics: str = Form(""),
    pdf_file: Optional[UploadFile] = File(None),
):
    """Generate a day-by-day study plan from an uploaded PDF and/or manual topics."""

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

    try:
        plan = generate_study_plan_with_llm(
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
        "plan": plan,
    }
