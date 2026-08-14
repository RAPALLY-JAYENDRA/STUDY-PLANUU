import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Study Planner",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ── Reset & Root ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1200px;
}

/* ── Hero header ── */
.hero-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 20px;
    padding: 3rem 2.5rem;
    margin-bottom: 2rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -60px; left: 50%; transform: translateX(-50%);
    width: 400px; height: 200px;
    background: radial-gradient(ellipse at center, rgba(99,102,241,0.25) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0 0 0.5rem;
    letter-spacing: -0.03em;
}
.hero-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    margin: 0;
    font-weight: 400;
}
.hero-badge {
    display: inline-block;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.35);
    color: #a5b4fc;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.3rem 0.9rem;
    border-radius: 99px;
    margin-bottom: 1rem;
}

/* ── Stat pills ── */
.stats-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
}
.stat-pill {
    flex: 1;
    min-width: 140px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    text-align: center;
}
.stat-pill .stat-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #6366f1;
    line-height: 1;
}
.stat-pill .stat-label {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.3rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Day cards ── */
.day-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
}
.day-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: #6366f1;
    border-radius: 4px 0 0 4px;
}
.day-card.completed::before { background: #22c55e; }
.day-card.beginner::before  { background: #22c55e; }
.day-card.intermediate::before { background: #f59e0b; }
.day-card.advanced::before  { background: #ef4444; }

.day-card:hover {
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 4px 24px rgba(99,102,241,0.08);
}

.day-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.75rem;
}
.day-number {
    background: rgba(99,102,241,0.15);
    color: #a5b4fc;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    padding: 0.25rem 0.7rem;
    border-radius: 8px;
    white-space: nowrap;
}
.day-topic {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #f1f5f9;
    flex: 1;
}
.difficulty-badge {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border-radius: 99px;
}
.difficulty-beginner     { background: rgba(34,197,94,0.15);  color: #4ade80; }
.difficulty-intermediate { background: rgba(245,158,11,0.15); color: #fbbf24; }
.difficulty-advanced     { background: rgba(239,68,68,0.15);  color: #f87171; }

.duration-tag {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.78rem;
    color: #64748b;
    white-space: nowrap;
}

.section-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #475569;
    margin: 0.9rem 0 0.35rem;
}
.tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}
.tag {
    background: #0f172a;
    border: 1px solid #334155;
    color: #94a3b8;
    font-size: 0.75rem;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
}
.concept-tag {
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.2);
    color: #a5b4fc;
}
.reading-box {
    background: #0f172a;
    border-left: 3px solid #6366f1;
    border-radius: 0 8px 8px 0;
    padding: 0.5rem 0.85rem;
    font-size: 0.82rem;
    color: #94a3b8;
    margin-top: 0.35rem;
    font-style: italic;
}
.tip-box {
    background: rgba(245,158,11,0.07);
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: 8px;
    padding: 0.5rem 0.85rem;
    font-size: 0.8rem;
    color: #fbbf24;
    margin-top: 0.35rem;
}
.task-item {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    font-size: 0.82rem;
    color: #94a3b8;
    padding: 0.2rem 0;
}
.task-bullet {
    color: #6366f1;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
}

/* ── Progress bar ── */
.progress-wrap {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.5rem;
}
.progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 0.6rem;
    font-weight: 500;
}
.progress-track {
    background: #0f172a;
    border-radius: 99px;
    height: 8px;
    overflow: hidden;
}
.progress-fill {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    height: 100%;
    border-radius: 99px;
    transition: width 0.4s ease;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #475569;
}
.empty-icon { font-size: 3.5rem; margin-bottom: 1rem; }
.empty-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.4rem;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 0.5rem;
}
.empty-desc { font-size: 0.9rem; }

/* ── Sidebar polish ── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] .stButton button {
    width: 100%;
    background: linear-gradient(135deg, #6366f1, #7c3aed);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.65rem;
    font-weight: 600;
    font-size: 0.95rem;
    letter-spacing: 0.01em;
    transition: opacity 0.2s;
}
[data-testid="stSidebar"] .stButton button:hover { opacity: 0.88; }

.stSpinner > div > div { border-top-color: #6366f1 !important; }

/* dark inputs */
input, textarea, select {
    background: #1e293b !important;
    color: #f1f5f9 !important;
    border-color: #334155 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────────
if "plan" not in st.session_state:
    st.session_state.plan = None
if "completed_days" not in st.session_state:
    st.session_state.completed_days = set()
if "subject" not in st.session_state:
    st.session_state.subject = ""


# ── Helpers ────────────────────────────────────────────────────────────────────
def call_backend(payload: dict, pdf_bytes=None, pdf_name=None) -> dict:
    try:
        files = {}
        if pdf_bytes:
            files["pdf_file"] = (pdf_name, pdf_bytes, "application/pdf")
        resp = requests.post(
            f"{BACKEND_URL}/generate-plan",
            data=payload,
            files=files if files else None,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach backend. Make sure the API server is running.")
        return {}
    except requests.exceptions.Timeout:
        st.error("⏱ Request timed out. The LLM is taking too long. Try fewer days.")
        return {}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"❌ API Error: {detail}")
        return {}


def difficulty_class(d: str) -> str:
    d = d.lower()
    if "begin" in d:
        return "beginner"
    if "inter" in d:
        return "intermediate"
    if "advan" in d:
        return "advanced"
    return "beginner"


def render_day_card(day_data: dict, idx: int):
    day_num = day_data.get("day", idx + 1)
    topic = day_data.get("topic", "—")
    subtopics = day_data.get("subtopics", [])
    reading = day_data.get("reading", "—")
    tasks = day_data.get("tasks", [])
    key_concepts = day_data.get("key_concepts", [])
    duration = day_data.get("estimated_duration", "—")
    difficulty = day_data.get("difficulty", "Beginner")
    tip = day_data.get("tips", "")

    diff_cls = difficulty_class(difficulty)
    is_done = day_num in st.session_state.completed_days
    card_cls = f"day-card {diff_cls}" + (" completed" if is_done else "")

    diff_badge_cls = f"difficulty-{diff_cls}"
    done_emoji = "✅ " if is_done else ""

    subtopics_html = "".join(f'<span class="tag">{s}</span>' for s in subtopics)
    concepts_html = "".join(
        f'<span class="tag concept-tag">{c}</span>' for c in key_concepts
    )
    tasks_html = "".join(
        f'<div class="task-item"><span class="task-bullet">›</span><span>{t}</span></div>'
        for t in tasks
    )

    html = f"""
<div class="{card_cls}">
  <div class="day-header">
    <span class="day-number">Day {day_num}</span>
    <span class="day-topic">{done_emoji}{topic}</span>
    <span class="difficulty-badge {diff_badge_cls}">{difficulty}</span>
    <span class="duration-tag">⏱ {duration}</span>
  </div>
  {'<div class="section-label">Subtopics</div><div class="tag-list">' + subtopics_html + '</div>' if subtopics else ''}
  <div class="section-label">📖 Reading / Reference</div>
  <div class="reading-box">{reading}</div>
  {'<div class="section-label">🔑 Key Concepts</div><div class="tag-list">' + concepts_html + '</div>' if key_concepts else ''}
  <div class="section-label">✅ Tasks</div>
  {tasks_html}
  {'<div class="section-label">💡 Tip</div><div class="tip-box">' + tip + '</div>' if tip else ''}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 6])
    with col_a:
        label = "Unmark" if is_done else "Mark Done"
        if st.button(label, key=f"mark_{day_num}"):
            if is_done:
                st.session_state.completed_days.discard(day_num)
            else:
                st.session_state.completed_days.add(day_num)
            st.rerun()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h2 style='color:#f1f5f9;font-family:Space Grotesk;font-weight:700;margin-bottom:0.2rem;'>⚙️ Plan Settings</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#64748b;font-size:0.82rem;margin-top:0;margin-bottom:1.5rem;'>Configure your study plan below</p>",
        unsafe_allow_html=True,
    )

    subject_name = st.text_input(
        "📘 Subject / Course Name",
        placeholder="e.g. Machine Learning, GATE CSE, Data Structures…",
        key="subject_input",
    )

    pdf_file = st.file_uploader(
        "📄 Upload Syllabus PDF (optional)",
        type=["pdf"],
        help="Upload your syllabus or textbook PDF for an exact-match plan.",
    )
    if pdf_file:
        st.success(f"✅ {pdf_file.name} uploaded ({pdf_file.size // 1024} KB)")

    manual_topics = st.text_area(
        "📝 Additional Topics (optional)",
        placeholder="List topics you want covered, one per line…\ne.g.\nLinear Algebra\nProbability & Statistics\nNeural Networks",
        height=130,
        help="These are combined with the PDF content.",
    )

    st.markdown("---")

    num_days = st.slider("📅 Study Duration (days)", 7, 180, 30, 1)
    hours_per_day = st.slider("⏱ Hours per Day", 0.5, 12.0, 4.0, 0.5)

    st.markdown("---")

    generate_clicked = st.button("🚀 Generate Study Plan", use_container_width=True)

    if st.session_state.plan:
        st.markdown("---")
        plan_json = json.dumps(
            {
                "subject": st.session_state.subject,
                "plan": st.session_state.plan,
                "completed_days": list(st.session_state.completed_days),
            },
            indent=2,
        )
        st.download_button(
            "⬇️ Download Plan (JSON)",
            data=plan_json,
            file_name=f"study_plan_{subject_name or 'plan'}.json",
            mime="application/json",
            use_container_width=True,
        )

        if st.button("🗑 Clear Plan", use_container_width=True):
            st.session_state.plan = None
            st.session_state.completed_days = set()
            st.rerun()


# ── Main area ──────────────────────────────────────────────────────────────────

# Hero
st.markdown(
    """
<div class="hero-header">
  <div class="hero-badge">Powered by Llama 3.3 · 70B via Groq</div>
  <h1 class="hero-title">📚 AI Study Planner</h1>
  <p class="hero-subtitle">Upload your syllabus or enter topics — get a precise, day-by-day study roadmap tailored exactly to your content.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Generate plan on button click ─────────────────────────────────────────────
if generate_clicked:
    if not pdf_file and not manual_topics.strip():
        st.warning("⚠️ Please upload a PDF or enter some topics before generating.")
    else:
        with st.spinner("🤖 AI is crafting your personalised study plan… this may take 20–40 seconds."):
            payload = {
                "num_days": num_days,
                "hours_per_day": hours_per_day,
                "subject_name": subject_name,
                "manual_topics": manual_topics,
            }
            pdf_bytes = pdf_file.read() if pdf_file else None
            pdf_name = pdf_file.name if pdf_file else None

            result = call_backend(payload, pdf_bytes, pdf_name)

        if result.get("success"):
            st.session_state.plan = result["plan"]
            st.session_state.subject = result.get("subject", subject_name)
            st.session_state.completed_days = set()
            st.success(
                f"✅ Generated a **{result['total_days']}-day** study plan for **{result.get('subject') or 'your course'}**!"
            )
            st.rerun()

# ── Render plan ────────────────────────────────────────────────────────────────
if st.session_state.plan:
    plan = st.session_state.plan
    total = len(plan)
    done = len(st.session_state.completed_days)
    pct = int(done / total * 100) if total else 0

    # Stats row
    st.markdown(
        f"""
<div class="stats-row">
  <div class="stat-pill">
    <div class="stat-num">{total}</div>
    <div class="stat-label">Total Days</div>
  </div>
  <div class="stat-pill">
    <div class="stat-num">{done}</div>
    <div class="stat-label">Completed</div>
  </div>
  <div class="stat-pill">
    <div class="stat-num">{total - done}</div>
    <div class="stat-label">Remaining</div>
  </div>
  <div class="stat-pill">
    <div class="stat-num">{pct}%</div>
    <div class="stat-label">Progress</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Progress bar
    st.markdown(
        f"""
<div class="progress-wrap">
  <div class="progress-label">
    <span>Overall Progress</span>
    <span>{done} / {total} days complete</span>
  </div>
  <div class="progress-track">
    <div class="progress-fill" style="width:{pct}%"></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Filter
    filter_opts = ["All Days", "Not Started", "Completed"]
    diff_opts = ["All Levels", "Beginner", "Intermediate", "Advanced"]

    fc1, fc2, fc3 = st.columns([2, 2, 3])
    with fc1:
        status_filter = st.selectbox("Filter by status", filter_opts, label_visibility="collapsed")
    with fc2:
        diff_filter = st.selectbox("Filter by difficulty", diff_opts, label_visibility="collapsed")
    with fc3:
        search_q = st.text_input("Search topics…", placeholder="🔍 Search…", label_visibility="collapsed")

    # Apply filters
    filtered = plan
    if status_filter == "Completed":
        filtered = [d for d in filtered if d.get("day") in st.session_state.completed_days]
    elif status_filter == "Not Started":
        filtered = [d for d in filtered if d.get("day") not in st.session_state.completed_days]
    if diff_filter != "All Levels":
        filtered = [
            d for d in filtered
            if diff_filter.lower() in d.get("difficulty", "").lower()
        ]
    if search_q.strip():
        q = search_q.lower()
        filtered = [
            d for d in filtered
            if q in d.get("topic", "").lower()
            or any(q in s.lower() for s in d.get("subtopics", []))
            or any(q in c.lower() for c in d.get("key_concepts", []))
        ]

    if not filtered:
        st.markdown(
            '<div class="empty-state"><div class="empty-icon">🔍</div>'
            '<div class="empty-title">No days match your filter</div>'
            '<div class="empty-desc">Try a different search or filter.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        for i, day_data in enumerate(filtered):
            render_day_card(day_data, i)

else:
    # Empty state
    st.markdown(
        """
<div class="empty-state">
  <div class="empty-icon">📖</div>
  <div class="empty-title">Your study plan will appear here</div>
  <div class="empty-desc">
    Use the sidebar on the left to upload your syllabus PDF, add topics,
    set your study duration, and click <strong>Generate Study Plan</strong>.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
