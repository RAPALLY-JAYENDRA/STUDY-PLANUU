/**
 * Cloudflare AI Worker — AI Study Planner
 *
 * Model: @cf/meta/llama-3.3-70b-instruct-fp8-fast
 *
 * Deploy:
 *   1. cd worker/
 *   2. npm install -g wrangler   (first time only)
 *   3. wrangler login
 *   4. wrangler deploy
 *
 * The deployed URL goes into your Railway env var: CLOUDFLARE_WORKER_URL
 *
 * Expected request body (JSON POST):
 * {
 *   "pdf_text"      : "...",
 *   "manual_topics" : "...",
 *   "num_days"      : 30,
 *   "hours_per_day" : 4.0,
 *   "subject_name"  : "Machine Learning"
 * }
 */

export default {
  async fetch(request, env) {
    // ── CORS pre-flight ────────────────────────────────────────────────────
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    // ── Health check ───────────────────────────────────────────────────────
    const url = new URL(request.url);
    if (url.pathname === "/health" || request.method === "GET") {
      return new Response(
        JSON.stringify({ status: "ok", service: "AI Study Planner Worker" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // ── Parse request ──────────────────────────────────────────────────────
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const {
      pdf_text = "",
      manual_topics = "",
      num_days = 30,
      hours_per_day = 4.0,
      subject_name = "General Study",
    } = body;

    if (!pdf_text.trim() && !manual_topics.trim()) {
      return new Response(
        JSON.stringify({ error: "Provide pdf_text or manual_topics" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // ── Build LLM prompt ───────────────────────────────────────────────────
    const contextParts = [];
    if (pdf_text.trim()) {
      // Truncate to ~25k chars to stay within context limits
      contextParts.push(`=== SYLLABUS / PDF CONTENT ===\n${pdf_text.slice(0, 25000)}`);
    }
    if (manual_topics.trim()) {
      contextParts.push(`=== ADDITIONAL TOPICS ===\n${manual_topics}`);
    }
    const contextBlock = contextParts.join("\n\n");

    const systemPrompt =
      "You are an expert educational study planner. " +
      "Analyse the provided syllabus/PDF content and produce a highly detailed, " +
      "realistic day-by-day study plan that maps exactly to the content. " +
      "Always respond with valid JSON only — no markdown fences, no commentary.";

    const userPrompt = `Subject: ${subject_name}
Total Study Days: ${num_days}
Hours Available Per Day: ${hours_per_day}

${contextBlock}

---

Create a JSON ARRAY of exactly ${num_days} day-plan objects. Each object MUST have:
  "day"                : integer (1 to ${num_days})
  "topic"              : string — the main topic for this day (must match content above)
  "subtopics"          : array of 2-5 strings — specific subtopics/sections
  "reading"            : string — exact chapter / section / page references
  "tasks"              : array of 3-5 actionable task strings
  "key_concepts"       : array of 3-6 important terms or concepts
  "estimated_duration" : string — total study time (e.g. "3.5 hours")
  "difficulty"         : string — "Beginner", "Intermediate", or "Advanced"
  "tips"               : string — one concise study tip for today

Rules:
- Distribute content evenly across all ${num_days} days.
- Earlier days = foundational/intro material; later days = deeper dives.
- Every day must reference REAL content from the provided text.
- Return ONLY a raw JSON array starting with [ and ending with ]. No other text.`;

    // ── Call Workers AI ────────────────────────────────────────────────────
    let aiResponse;
    try {
      aiResponse = await env.AI.run("@cf/meta/llama-3.3-70b-instruct-fp8-fast", {
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user",   content: userPrompt },
        ],
        temperature: 0.25,
        max_tokens: 8192,
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: `Workers AI error: ${err.message}` }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const rawText = (aiResponse?.response || "").trim();

    // ── Parse JSON from LLM output ─────────────────────────────────────────
    let plan;
    try {
      // Strip markdown code fences if model adds them
      const cleaned = rawText
        .replace(/^```(?:json)?\s*/i, "")
        .replace(/\s*```$/,          "");

      // Find the JSON array
      const match = cleaned.match(/\[[\s\S]*\]/);
      plan = JSON.parse(match ? match[0] : cleaned);
    } catch (err) {
      return new Response(
        JSON.stringify({
          error: "LLM returned malformed JSON. Try again.",
          raw: rawText.slice(0, 500),
        }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // ── Return success ─────────────────────────────────────────────────────
    return new Response(
      JSON.stringify({
        success: true,
        subject: subject_name,
        total_days: plan.length,
        hours_per_day,
        plan,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  },
};
