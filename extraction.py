"""
extraction.py — US-AG-01 (parse JD + resume) and US-AG-02 (generate question plan).

Pipeline:
  1. extract_text()        — pull raw text from a PDF (pypdf, no OCR — scanned PDFs won't work)
  2. analyze_documents()   — LLM extracts candidate name/email, experience level, skills,
                             gap analysis (JD vs resume). Uses the Gemini-first parsing chain.
  3. generate_question_plan() — LLM builds a structured, level-appropriate question plan tailored
                             to the candidate, replacing the static sample_questions.json.

Prompt design adapted from the other team's claude.py; routed through our llm_stack (Gemini→Claude→Groq).
"""
import os, json, logging
from pypdf import PdfReader
import llm_stack

logger = logging.getLogger("extraction")


# ─── 1. PDF TEXT EXTRACTION (no OCR) ──────────────────────
def extract_text(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")
    text = ""
    try:
        for page in PdfReader(file_path).pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {e}")
    return text.strip()


# ─── 2. ANALYZE JD + RESUME ───────────────────────────────
def analyze_documents(jd_text: str, resume_text: str, role: str = "Software Engineer",
                      keys: dict = None) -> dict:
    system = ("You are a senior technical recruiter with 15+ years experience. Analyse resumes and "
              "JDs with precision. ALWAYS return ONLY valid JSON — no prose, no markdown.")
    user = f"""Analyse this resume against the job description and return a structured analysis.

JOB DESCRIPTION:
{jd_text or f"Role: {role} — no JD provided"}

CANDIDATE RESUME:
{resume_text or "No resume provided"}

Rules:
- Detect experience level from years of experience, job titles, project complexity, responsibilities.
- "Fresher (0-1 year)" = <1 year, "Experienced (1-3 years)" = 1-3 years, "Experienced (3-5 years)" = 3-5 years, "Experienced (5+ years)" = 5+ years.
- Scan the resume text for the candidate's email address if present.

Return EXACTLY this JSON (no deviations):
{{
  "candidateName": "extracted full name or 'Candidate'",
  "candidateEmail": "extracted email or null",
  "jobRole": "the specific role title from the JD or the provided role",
  "detectedLevel": "Fresher (0-1 year)|Experienced (1-3 years)|Experienced (3-5 years)|Experienced (5+ years)",
  "levelReason": "one short line (e.g. '3 years React experience')",
  "yearsExperience": 0,
  "skills": ["..."],
  "technicalStack": ["..."],
  "missingSkills": ["skills in the JD weak/absent in the resume"],
  "jdMatchScore": 0,
  "analysisSummary": "One-line summary of resume and JD gap"
}}"""
    result = llm_stack.call_json(system, user, job="parsing", max_tokens=1200, keys=keys)
    if not result:
        logger.warning("analyze_documents: parse failed, returning minimal fallback")
        return {"candidateName": "Candidate", "candidateEmail": None, "jobRole": role,
                "detectedLevel": "Fresher (0-1 year)", "levelReason": "", "yearsExperience": 0,
                "skills": [], "technicalStack": [], "missingSkills": [], "jdMatchScore": 0,
                "analysisSummary": ""}
    return result


# ─── 3. GENERATE DYNAMIC QUESTION PLAN (US-AG-02) ─────────
def generate_question_plan(analysis: dict, role: str = None, question_count: int = 12,
                           keys: dict = None) -> list:
    """
    Returns a list of question dicts:
      {question, topic, question_type, depth, target_skill, key_concepts:[...]}
    matching the shape our interview engine expects (question + topic + key_concepts).
    """
    role = role or analysis.get("jobRole", "Software Engineer")
    level = analysis.get("detectedLevel", "Fresher (0-1 year)")
    level_flow = {
        "Fresher (0-1 year)": "1.Core fundamentals 2.Basic problem-solving 3.Projects 4.Theory 5.Motivation 6.Career goals",
        "Experienced (1-3 years)": "1.Core tech 2.Hands-on implementation 3.Debugging/trade-offs 4.Collaboration 5.Motivation 6.Career goals",
        "Experienced (3-5 years)": "1.Core tech 2.Hands-on implementation 3.Debugging/trade-offs 4.Collaboration 5.Motivation 6.Career goals",
        "Experienced (5+ years)": "1.Complex challenges 2.Team leadership 3.System design/strategy 4.Motivation 5.Career goals",
    }.get(level, "1.Core fundamentals 2.Problem-solving 3.Projects 4.Motivation 5.Career goals")

    system = ("You are a world-class technical interviewer. Generate precise, insightful interview "
              "questions tailored to the candidate. ALWAYS return ONLY a valid JSON array.")
    user = f"""Generate a structured interview question plan.

ROLE: {role}
CANDIDATE LEVEL: {level}  ({analysis.get('levelReason','')})
SKILLS FROM RESUME: {', '.join(analysis.get('skills', []) or [])}
TECH STACK: {', '.join(analysis.get('technicalStack', []) or [])}
GAP / MISSING SKILLS (skills the JD requires that the resume lacks): {', '.join(analysis.get('missingSkills', []) or [])}
BRIEFING: {analysis.get('analysisSummary','')}

FLOW (follow this order): {level_flow}
Structure: introduction → core technology → practical/scenario → gap areas → closing.
Generate EXACTLY {max(10, min(question_count, 20))} questions (spec requires 10-20).

CRITICAL DIFFICULTY-TO-SOURCE MAPPING (follow strictly):
- "surface" and "medium" depth questions MUST be grounded in the RESUME: verify the candidate can
  genuinely explain the skills, projects, and experience THEY CLAIM. Reference their actual listed
  skills/projects so a bluffer is exposed and an honest candidate can shine.
- "deep" depth questions MUST target the GAP / MISSING SKILLS: probe whether the candidate has
  adjacent knowledge, transferable experience, or learning aptitude for what the JD expects but the
  resume does not show — i.e., if they join the company, can they adapt to those concepts?
- Difficulty progresses through the interview: early questions surface, middle medium, late deep.

Return ONLY a JSON array, each item EXACTLY:
[
  {{
    "question": "the question text, phrased for being read aloud (TTS) — natural and clear",
    "topic": "short topic label (e.g. 'System Design')",
    "question_type": "technical|behavioral|scenario|introduction|closing",
    "depth": "surface|medium|deep",
    "target_skill": "the skill this probes",
    "key_concepts": ["concept the answer should cover", "..."]
  }}
]"""
    plan = llm_stack.call_json(system, user, job="parsing", max_tokens=3000, keys=keys)
    if not plan or not isinstance(plan, list):
        logger.warning("generate_question_plan: parse failed — falling back to static questions")
        return _static_fallback()
    # sanity: ensure each has the fields our engine needs
    clean = []
    for q in plan:
        if not isinstance(q, dict) or not q.get("question"):
            continue
        clean.append({
            "question": q.get("question", "").strip(),
            "topic": q.get("topic", "General"),
            "question_type": q.get("question_type", "technical"),
            "depth": q.get("depth", "medium"),
            "target_skill": q.get("target_skill", ""),
            "key_concepts": q.get("key_concepts", []) if isinstance(q.get("key_concepts"), list) else [],
        })
    return clean or _static_fallback()


def _static_fallback() -> list:
    """If generation fails, fall back to the original static questions so an interview still runs."""
    try:
        with open("speech_interview_logic/sample_questions.json") as f:
            return json.load(f)
    except Exception:
        return [{"question": "Can you briefly introduce yourself and your current role?",
                 "topic": "Introduction", "question_type": "introduction", "depth": "surface",
                 "target_skill": "communication", "key_concepts": ["role", "experience"]}]