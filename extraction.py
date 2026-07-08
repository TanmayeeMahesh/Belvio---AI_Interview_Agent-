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
import os, json, logging, re
from pypdf import PdfReader
import llm_stack

logger = logging.getLogger("extraction")

QUESTION_BANK_PATH = os.path.join(os.path.dirname(__file__), "question_bank.md")
REQUIRED_CATEGORIES = [
    "Core Concepts",
    "Role-Specific Fundamentals",
    "Tools & Technologies",
    "Frameworks & Methodologies",
    "Industry Knowledge",
]


def _normalize_role_name(role: str) -> str:
    if not role:
        return ""
    return re.sub(r"\s+", " ", role).strip().lower()


def _normalize_category_name(category: str) -> str:
    if not category:
        return ""
    return re.sub(r"\s+", " ", category).strip()


def _parse_question_bank(path: str = None) -> dict:
    bank_path = path or QUESTION_BANK_PATH
    if not os.path.exists(bank_path):
        return {}

    role_data = {}
    current_role = None
    current_category = None
    current_tier = None

    with open(bank_path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            role_match = re.match(r"^##\s+\d+\.\s+(.*)$", line)
            if role_match:
                current_role = _normalize_role_name(role_match.group(1))
                role_data[current_role] = {}
                current_category = None
                current_tier = None
                continue

            category_match = re.match(r"^###\s+(.*)$", line)
            if category_match:
                current_category = _normalize_category_name(category_match.group(1))
                current_tier = None
                if current_role:
                    role_data[current_role][current_category] = {}
                continue

            tier_match = re.match(r"^####\s+(.*)$", line)
            if tier_match:
                current_tier = tier_match.group(1)
                if current_role and current_category:
                    role_data[current_role][current_category][current_tier] = []
                continue

            question_match = re.match(r"^\d+\.\s+(.*)$", line)
            if question_match and current_role and current_category and current_tier:
                role_data[current_role][current_category][current_tier].append(question_match.group(1))

    return role_data


def _find_matching_role(question_bank: dict, role: str) -> str:
    if not question_bank:
        return ""

    normalized_role = _normalize_role_name(role)
    if not normalized_role:
        return ""

    if normalized_role in question_bank:
        return normalized_role

    for existing_role in question_bank:
        if normalized_role in existing_role or existing_role in normalized_role:
            return existing_role

    return ""


def _experience_tier_for_analysis(analysis: dict) -> str:
    level = (analysis.get("detectedLevel") or "").lower()
    years = int(analysis.get("yearsExperience") or 0)

    if level == "fresher" or years < 1:
        return "Fresher (0–1 year of experience)"
    if years < 3 and level != "experienced":
        return "Experienced (1–3 years of experience)"
    if years < 5:
        return "Experienced (3–5 years of experience)"
    return "Experienced (5+ years of experience)"


def _missing_skill_category(skill: str) -> str:
    if not skill:
        return ""
    s = skill.lower()
    if any(k in s for k in ["docker", "git", "sql", "python", "java", "aws", "azure", "linux", "kubernetes", "cloud"]):
        return "Tools & Technologies"
    if any(k in s for k in ["design", "system", "architecture", "agile", "scrum", "kanban", "method", "framework"]):
        return "Frameworks & Methodologies"
    if any(k in s for k in ["security", "compliance", "industry", "regulation", "business"]):
        return "Industry Knowledge"
    return ""


def _build_gap_question(skill: str, category: str) -> dict:
    skill_text = skill.strip()
    if category == "Tools & Technologies":
        question = f"Can you walk us through your experience with {skill_text} and explain how you have used it in real projects?"
        question_type = "technical"
    elif category == "Frameworks & Methodologies":
        question = f"How would you apply {skill_text} in a real-world project, and what trade-offs would you consider?"
        question_type = "technical"
    elif category == "Role-Specific Fundamentals":
        question = f"How would you approach {skill_text} in a typical role-specific scenario?"
        question_type = "behavioral"
    elif category == "Industry Knowledge":
        question = f"How do you stay current with {skill_text} and apply it in your work?"
        question_type = "behavioral"
    else:
        question = f"How would you explain {skill_text} to a teammate or interviewer in a practical setting?"
        question_type = "technical"

    return {
        "question": question,
        "topic": category,
        "question_type": question_type,
        "depth": "deep",
        "target_skill": skill_text.lower(),
        "key_concepts": [skill_text],
        "selection_reason": "gap",
        "gap_skill": skill_text,
        "source": "gap_analysis",
    }


def select_questions_from_question_bank(analysis: dict, role: str = None,
                                        question_count: int = 5,
                                        path: str = None) -> list:
    """Select a compact, experience-aware set of questions from the markdown question bank."""
    if question_count <= 0:
        return []

    question_bank = _parse_question_bank(path)
    if not question_bank:
        return []

    role_name = _find_matching_role(question_bank, role or analysis.get("jobRole", "Software Engineer"))
    if not role_name:
        return []

    selected = []
    tier_name = _experience_tier_for_analysis(analysis)
    missing_skills = analysis.get("missingSkills") or []
    gap_skills = []

    for skill in missing_skills:
        mapped_category = _missing_skill_category(skill)
        if mapped_category in REQUIRED_CATEGORIES:
            gap_skills.append((mapped_category, skill))

    gap_skills = gap_skills[:2]

    for category in REQUIRED_CATEGORIES:
        category_questions = question_bank.get(role_name, {}).get(category, {})
        if not category_questions:
            continue

        tier_questions = category_questions.get(tier_name, [])
        if not tier_questions:
            tier_questions = []
            for questions in category_questions.values():
                if questions:
                    tier_questions = questions
                    break

        if not tier_questions:
            continue

        selected.append({
            "question": tier_questions[0],
            "topic": category,
            "question_type": "behavioral" if category in ["Role-Specific Fundamentals", "Industry Knowledge"] else "technical",
            "depth": "surface" if tier_name.startswith("Fresher") else "medium",
            "target_skill": category.lower(),
            "key_concepts": [category],
            "selection_reason": "experience",
            "source": "question_bank",
        })

        if len(selected) >= 5:
            break

    for category, skill in gap_skills:
        selected.append(_build_gap_question(skill, category))

    return selected[: question_count + len(gap_skills)]


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
- fresher = <1 year, intermediate = 1-5 years, experienced = 5+ years.
- Scan the resume text for the candidate's email address if present.

Return EXACTLY this JSON (no deviations):
{{
  "candidateName": "extracted full name or 'Candidate'",
  "candidateEmail": "extracted email or null",
  "jobRole": "the specific role title from the JD or the provided role",
  "detectedLevel": "fresher|intermediate|experienced",
  "levelReason": "one short line (e.g. '3 years React experience')",
  "yearsExperience": 0,
  "skills": ["..."],
  "technicalStack": ["..."],
  "missingSkills": ["skills in the JD weak/absent in the resume"],
  "jdMatchScore": 0,
  "analysisSummary": "2-3 sentence briefing for the interviewer agent"
}}"""
    result = llm_stack.call_json(system, user, job="parsing", max_tokens=1200, keys=keys)
    if not result:
        logger.warning("analyze_documents: parse failed, returning minimal fallback")
        return {"candidateName": "Candidate", "candidateEmail": None, "jobRole": role,
                "detectedLevel": "fresher", "levelReason": "", "yearsExperience": 0,
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
    level = analysis.get("detectedLevel", "fresher")
    level_flow = {
        "fresher": "1.Core fundamentals 2.Basic problem-solving 3.Projects 4.Theory 5.Motivation 6.Career goals",
        "intermediate": "1.Core tech 2.Hands-on implementation 3.Debugging/trade-offs 4.Collaboration 5.Motivation 6.Career goals",
        "experienced": "1.Complex challenges 2.Team leadership 3.System design/strategy 4.Motivation 5.Career goals",
    }.get(level, "1.Core fundamentals 2.Problem-solving 3.Projects 4.Motivation 5.Career goals")

    # Prefer curated questions from the markdown bank first, using the candidate's experience
    # level and the resume/JD gap analysis to select questions.
    bank_questions = select_questions_from_question_bank(
        analysis,
        role=role,
        question_count=5,
    )
    if bank_questions:
        return bank_questions

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