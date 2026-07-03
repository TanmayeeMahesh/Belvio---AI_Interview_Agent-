"""
proctor.py — Post-interview INTEGRITY analysis (Mode A). Fail-safe, runs in a background thread.

v1 (this file): TRANSCRIPT AUTHENTICITY only — a text-only check that flags answers which read like
they were copied from an AI (ChatGPT etc.) rather than spoken spontaneously. No video/CV yet, so it
adds NO new dependencies (uses the Groq client we already run) and is fully testable locally.

Video signals (face presence, second person, phone via MediaPipe + cloud vision) are a LATER task.

Design rules:
  - NEVER raises into the caller — any failure saves {assessed: false} and returns.
  - Outputs are FLAGS FOR HUMAN REVIEW, not verdicts (AI-text detection has false positives).
  - Writes to the integrity_reports table (decoupled from reports → no write race with the evaluator).
"""
import os, json
from groq import Groq
from dotenv import load_dotenv
import db

load_dotenv()

_PROCTOR_MODEL = "llama-3.3-70b-versatile"   # text reasoning; runs in background, latency hidden
_groq = None
def _client():
    global _groq
    if _groq is None:
        _groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq


def _candidate_answers(session_id):
    """Pull the candidate's answers (paired with their question) from the transcript rows."""
    rows = db.read_answers(session_id)
    by_qid = {}
    for r in rows:
        qid = r.get("q_id")
        if not qid or qid in ("intro", "closing"):
            continue
        slot = by_qid.setdefault(qid, {"topic": r.get("topic"), "question": "", "answer": ""})
        role = r.get("role")
        text = (r.get("text") or "").strip()
        if role in ("question", "followup_question"):
            slot["question"] = text
        elif role in ("answer", "followup_answer"):
            slot["answer"] = (slot["answer"] + " " + text).strip()
    return [s for s in by_qid.values() if s.get("answer")]


def analyze_transcript_authenticity(session_id):
    """
    LLM check: does any answer read like it was copied from AI rather than spoken spontaneously?
    Returns {ai_likelihood: low|medium|high, flagged_answers: [...]}. SOFT signal for review only.
    """
    pairs = _candidate_answers(session_id)
    if not pairs:
        return {"ai_likelihood": "unknown", "flagged_answers": [], "note": "no answers to analyse"}

    transcript = "\n\n".join(
        f"TOPIC: {p['topic']}\nQ: {p['question']}\nA: {p['answer']}" for p in pairs)
    prompt = f"""You are checking interview answers for signs they were READ FROM AI-GENERATED TEXT
(e.g. copied from ChatGPT) instead of spoken spontaneously. The input is speech-to-text.

Signs of AI-read answers: essay-like structure ("firstly... secondly... in conclusion"), textbook or
overly formal register unusual for speech, unnaturally complete and polished, vocabulary that doesn't
match conversational talk.
Signs of genuine speech: hesitation, self-correction, informal phrasing, personal specifics, imperfect
structure.

IMPORTANT: this is a SOFT signal for human review, NOT proof. Articulate or well-prepared candidates,
and non-native speakers who rehearsed, can sound polished honestly. Be CONSERVATIVE — do not over-flag.

TRANSCRIPT:
{transcript}

Reply ONLY valid JSON, no markdown:
{{"ai_likelihood":"low|medium|high",
"flagged_answers":[{{"topic":"<topic>","reason":"<short reason, <=12 words>"}}]}}"""
    try:
        resp = _client().chat.completions.create(
            model=_PROCTOR_MODEL, messages=[{"role": "user", "content": prompt}],
            max_tokens=400, temperature=0.2)
        raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        r = json.loads(raw)
        r.setdefault("ai_likelihood", "low")
        r.setdefault("flagged_answers", [])
        return r
    except Exception as e:
        print(f"[PROCTOR] transcript authenticity failed: {e}")
        return {"ai_likelihood": "unknown", "flagged_answers": [], "note": "analysis failed"}


def _overall_flag(transcript_auth):
    """Combine signals into clean|minor|significant. v1 is transcript-driven; video adds to this later."""
    lvl = (transcript_auth or {}).get("ai_likelihood", "low")
    if lvl == "high":
        return "significant"
    if lvl == "medium":
        return "minor"
    return "clean"


def _summary(flag, transcript_auth):
    n = len(transcript_auth.get("flagged_answers", []))
    if flag == "clean":
        return "No integrity concerns detected in the transcript."
    return (f"{n} answer(s) flagged as possibly AI-assisted "
            f"({transcript_auth.get('ai_likelihood')} likelihood) — review recommended.")


def analyze_session(session_id, bot_id=None):
    """
    MAIN ENTRY — runs post-interview in a daemon thread. Fail-safe: never raises.
    v1 does the text-only transcript-authenticity check; video analysis is a later task (bot_id is
    accepted now so the signature stays stable when video is added).
    """
    try:
        print(f"[PROCTOR] analysing session {session_id}...")
        ta = analyze_transcript_authenticity(session_id)
        flag = _overall_flag(ta)
        result = {
            "assessed": True,
            "integrity_flag": flag,
            "transcript_authenticity": ta,
            "video": {"assessed": False, "note": "video analysis not enabled yet"},
            "summary": _summary(flag, ta),
        }
        db.save_integrity_report(session_id, result)
        print(f"[PROCTOR] session {session_id} → {flag}")
    except Exception as e:
        print(f"[PROCTOR] analyze_session failed: {e}")
        db.save_integrity_report(session_id, {"assessed": False, "note": f"error: {e}"})
