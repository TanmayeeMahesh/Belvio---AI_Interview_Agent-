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
import re

_gap_model = None
_gap_tokenizer = None

def _load_gap_model():
    global _gap_model, _gap_tokenizer
    if _gap_model is None:
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            model_dir = "flan_t5_finetuned_local_save"
            _gap_tokenizer = AutoTokenizer.from_pretrained(model_dir)
            _gap_model = AutoModelForSeq2SeqLM.from_pretrained(model_dir)
        except Exception as e:
            logger.error(f"Failed to load local GAP model: {e}")

def parse_question_bank(job_role: str, level: str) -> list:
    level_map = {
        "fresher": ["Fresher (0–1 year of experience)"],
        "intermediate": ["Experienced (1–3 years of experience)", "Experienced (3–5 years of experience)"],
        "experienced": ["Experienced (5+ years of experience)"]
    }
    
    target_levels = level_map.get(level.lower(), level_map["intermediate"])
    
    try:
        with open("question_bank.md", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    roles = re.split(r'\n## \d+\.\s+', content)
    
    best_role_chunk = None
    for chunk in roles[1:]:
        role_title = chunk.split('\n')[0].strip().lower()
        if job_role.lower() in role_title or role_title in job_role.lower():
            best_role_chunk = chunk
            break
            
    if not best_role_chunk:
        best_role_chunk = roles[1] if len(roles) > 1 else ""

    categories = re.split(r'\n###\s+', best_role_chunk)
    questions = []

    for cat_chunk in categories[1:]:
        lines = cat_chunk.split('\n')
        topic = lines[0].strip()
        
        current_level_match = False
        cat_q = []
        for line in lines[1:]:
            if line.startswith('#### '):
                level_title = line.replace('#### ', '').strip()
                current_level_match = any(t in level_title for t in target_levels)
            elif current_level_match and re.match(r'^\d+\.\s+', line):
                q_text = re.sub(r'^\d+\.\s+', '', line).strip()
                cat_q.append(q_text)
                
        if cat_q:
            questions.append({
                "question": cat_q[0],
                "topic": topic,
                "question_type": "technical",
                "depth": "medium" if level == "intermediate" else ("surface" if level == "fresher" else "deep"),
                "target_skill": topic,
                "key_concepts": [topic]
            })
            
    return questions[:5]


def generate_gap_questions(jd_text: str, resume_text: str) -> list:
    _load_gap_model()
    if not _gap_model or not _gap_tokenizer:
        return []
        
    try:
        # We skip the first 200 characters of the resume to bypass the contact info (Name, Email, Phone) 
        # which confuses the model into thinking it's a job title. We also add an instruction.
        clean_resume = resume_text[200:1200] if len(resume_text) > 200 else resume_text
        prompt = f"Generate interview questions about the candidate's missing skills based on the JD. JD: {jd_text[:1000]} Resume: {clean_resume}"
        inputs = _gap_tokenizer(prompt, return_tensors="pt")
        outputs = _gap_model.generate(**inputs, max_new_tokens=150)
        text = _gap_tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Split the text by numbers followed by a dot or parenthesis, e.g., ' 2) ' or ' 2. ' or '^1) '
        parts = re.split(r'(?:^|\s+)\d+[\.\)]\s*', text)
        clean_lines = [p.strip() for p in parts if p.strip()]
        # Just grab the first two lines that seem like reasonable questions/statements
        questions_text = [q for q in clean_lines if len(q) > 10][:2]
        
        gap_questions = []
        for q_text in questions_text:
            gap_questions.append({
                "question": q_text,
                "topic": "Gap Skills",
                "question_type": "technical",
                "depth": "deep",
                "target_skill": "Missing Skills",
                "key_concepts": ["Missing Skills"]
            })
        return gap_questions
    except Exception as e:
        logger.error(f"Failed to generate gap questions: {e}")
        return []

def generate_question_plan(analysis: dict, role: str = None, jd_text: str = "", resume_text: str = "") -> list:
    role = role or analysis.get("jobRole", "Software Engineer")
    level = analysis.get("detectedLevel", "fresher")

    questions = []
    
    questions.append({
        "question": "To begin, could you please introduce yourself? Feel free to walk us through your educational background, professional experience, and anything else you'd like us to know.",
        "topic": "Introduction",
        "question_type": "introduction",
        "depth": "surface",
        "target_skill": "communication",
        "key_concepts": ["introduction", "background"]
    })
    questions.append({
        "question": "Could you tell us about a project you've worked on that you're particularly proud of? Please describe the problem you were solving, your specific role and contributions, the tools or technologies you used, and the final outcome or impact.",
        "topic": "Projects",
        "question_type": "behavioral",
        "depth": "medium",
        "target_skill": "experience",
        "key_concepts": ["project", "impact", "tools"]
    })
    
    bank_questions = parse_question_bank(role, level)
    questions.extend(bank_questions)
    
    if jd_text and resume_text:
        gap_questions = generate_gap_questions(jd_text, resume_text)
        questions.extend(gap_questions)
        
    questions.append({
        "question": "As we wrap up, where do you see yourself professionally over the next five years, and how do you feel this role would fit into that journey?",
        "topic": "Career Goals",
        "question_type": "closing",
        "depth": "medium",
        "target_skill": "motivation",
        "key_concepts": ["future", "goals"]
    })
    questions.append({
        "question": "Finally, do you have any questions for us — about the role, the team, the company, or anything else you'd like to know before we conclude the interview?",
        "topic": "Candidate Questions",
        "question_type": "closing",
        "depth": "surface",
        "target_skill": "curiosity",
        "key_concepts": ["questions"]
    })
    
    return questions