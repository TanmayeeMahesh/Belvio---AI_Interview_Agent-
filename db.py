"""
db.py — Supabase persistence for the interview bot (Size 1: save-as-you-go, one interview at a time).
All functions fail SAFE: if Supabase is unreachable, they log and return None so the live
interview is never interrupted by a DB problem. The local JSON transcript remains the backup.
"""
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Lazy client so a missing/broken config doesn't crash import
_client = None
def _db():
    global _client
    if _client is None:
        try:
            from supabase import create_client
            _client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
            print("[DB]  Supabase client ready")
        except Exception as e:
            print(f"[ERROR] Supabase init failed (interview will still run): {e}")
            _client = False          # mark as failed so we don't retry every call
    return _client or None


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_session(bot_id: str, total_questions: int,
                   candidate_name: str = None, candidate_email: str = None,
                   role: str = None, status: str = "in_progress") -> str | None:
    """
    Create a candidate (minimal for now) + a session row. Returns session_id (uuid str) or None.
    status: 'in_progress' for live/manual starts; 'scheduled' when created at schedule time.
    """
    db = _db()
    if not db:
        return None
    try:
        cand = db.table("candidates").insert({
            "name": candidate_name, "email": candidate_email, "role": role,
        }).execute()
        candidate_id = cand.data[0]["id"]
        sess = db.table("sessions").insert({
            "candidate_id": candidate_id, "bot_id": bot_id,
            "status": status, "total_questions": total_questions,
            "started_at": _now(),
        }).execute()
        sid = sess.data[0]["id"]
        print(f"[DB]  session created → {sid} ({status})")
        return sid
    except Exception as e:
        print(f"[ERROR] create_session() failed (continuing without DB): {e}")
        return None


def mark_session_started(session_id: str) -> None:
    """Flip a scheduled session to in_progress when the candidate consents and the interview begins."""
    db = _db()
    if not db or not session_id:
        return
    try:
        db.table("sessions").update({"status": "in_progress", "started_at": _now()}) \
          .eq("id", session_id).execute()
    except Exception as e:
        print(f"[ERROR] mark_session_started() failed: {e}")


def insert_answer(session_id: str, q_id: str, role: str, speaker: str,
                  topic: str, text: str, category: str = None) -> None:
    """Insert one transcript row (question / answer / followup_* / intro / closing)."""
    db = _db()
    if not db or not session_id:
        return
    try:
        db.table("answers").insert({
            "session_id": session_id, "q_id": q_id, "role": role,
            "speaker": speaker, "topic": topic, "text": text,
            "category": category, "created_at": _now(),
        }).execute()
    except Exception as e:
        print(f"[ERROR] insert_answer() failed (continuing): {e}")


def close_session(session_id: str, status: str, questions_reached: int) -> None:
    """Mark the session finished with its completion status."""
    db = _db()
    if not db or not session_id:
        return
    try:
        db.table("sessions").update({
            "status": status, "questions_reached": questions_reached,
            "ended_at": _now(),
        }).eq("id", session_id).execute()
        print(f"[DB]  session closed → {status}")
    except Exception as e:
        print(f"[ERROR] close_session() failed: {e}")


def read_answers(session_id: str) -> list:
    """Read all answer rows for a session, ordered by time (for the final evaluation)."""
    db = _db()
    if not db or not session_id:
        return []
    try:
        res = (db.table("answers").select("*")
               .eq("session_id", session_id)
               .order("created_at").execute())
        return res.data or []
    except Exception as e:
        print(f"[ERROR] read_answers() failed: {e}")
        return []


def get_session_context(session_id: str) -> dict:
    """Return concise JD/resume analysis fields for the scorer (keeps prompts small)."""
    db = _db()
    if not db or not session_id:
        return {}
    try:
        res = db.table("sessions").select(
            "role, key_skills, missing_skills, analysis_summary, jd_match_score"
        ).eq("id", session_id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[ERROR] get_session_context() failed: {e}")
        return {}


def get_candidate_for_session(session_id: str) -> dict:
    """Fetch candidate name/email/role linked to a session (for the report header)."""
    db = _db()
    if not db or not session_id:
        return {}
    try:
        sess = db.table("sessions").select("candidate_id").eq("id", session_id).execute()
        if not sess.data:
            return {}
        cid = sess.data[0]["candidate_id"]
        cand = db.table("candidates").select("*").eq("id", cid).execute()
        return cand.data[0] if cand.data else {}
    except Exception as e:
        print(f"[ERROR] get_candidate_for_session() failed: {e}")
        return {}


def save_report(session_id: str, report: dict) -> None:
    """Upsert the final report row (one per session)."""
    db = _db()
    if not db or not session_id:
        return
    try:
        row = {"session_id": session_id, **report}
        db.table("reports").upsert(row, on_conflict="session_id").execute()
        print(f"[DB]  report saved for session {session_id}")
    except Exception as e:
        print(f"[ERROR] save_report() failed: {e}")


def save_recording_url(session_id: str, url: str) -> None:
    """Store the Recall MP4 recording URL on the session (for the HR dashboard)."""
    db = _db()
    if not db or not session_id or not url:
        return
    try:
        db.table("sessions").update({"recording_url": url}).eq("id", session_id).execute()
        print(f"[DB]  recording_url saved for session {session_id}")
    except Exception as e:
        print(f"[ERROR] save_recording_url() failed: {e}")


# ─── SCHEDULED INTERVIEWS (robust, survives restarts) ─────
def create_scheduled_interview(meeting_url: str, scheduled_for_iso: str,
                               candidate_email: str = None, candidate_name: str = None,
                               role: str = None, session_id: str = None) -> dict | None:
    """Insert a scheduled-interview row. Returns the row (with id) or None."""
    db = _db()
    if not db:
        return None
    try:
        res = db.table("scheduled_interviews").insert({
            "meeting_url": meeting_url, "scheduled_for": scheduled_for_iso,
            "candidate_email": candidate_email, "candidate_name": candidate_name,
            "role": role, "status": "scheduled", "session_id": session_id,
        }).execute()
        row = res.data[0]
        print(f"🗓️  scheduled interview {row['id']} for {scheduled_for_iso}")
        return row
    except Exception as e:
        print(f"[ERROR] create_scheduled_interview() failed: {e}")
        return None


def set_session_bot_id(session_id: str, bot_id: str) -> None:
    """Link a pre-created session (made at schedule time) to the bot that's now running it."""
    db = _db()
    if not db or not session_id:
        return
    try:
        db.table("sessions").update({"bot_id": bot_id}).eq("id", session_id).execute()
    except Exception as e:
        print(f"[ERROR] set_session_bot_id() failed: {e}")


def due_scheduled_interviews() -> list:
    """Rows that are due now (scheduled_for <= now) and still 'scheduled'."""
    db = _db()
    if not db:
        return []
    try:
        res = (db.table("scheduled_interviews").select("*")
               .eq("status", "scheduled")
               .lte("scheduled_for", _now())
               .order("scheduled_for").execute())
        return res.data or []
    except Exception as e:
        print(f"[ERROR] due_scheduled_interviews() failed: {e}")
        return []


def update_scheduled_interview(row_id: str, **fields) -> None:
    """Patch a scheduled-interview row (status, bot_id, email_sent, ...)."""
    db = _db()
    if not db or not row_id:
        return
    try:
        db.table("scheduled_interviews").update(fields).eq("id", row_id).execute()
    except Exception as e:
        print(f"[ERROR] update_scheduled_interview() failed: {e}")


def list_scheduled_interviews(limit: int = 50) -> list:
    """All scheduled interviews, newest first (for the operator UI/dashboard)."""
    db = _db()
    if not db:
        return []
    try:
        res = (db.table("scheduled_interviews").select("*")
               .order("created_at", desc=True).limit(limit).execute())
        return res.data or []
    except Exception as e:
        print(f"[ERROR] list_scheduled_interviews() failed: {e}")
        return []


# ─── ANALYSIS + QUESTIONS + DASHBOARD READS ───────────────
def update_session_analysis(session_id, analysis: dict, meeting_url: str,
                            scheduled_for_iso: str, jd_text=None, resume_text=None) -> None:
    """Store the JD/resume analysis + scheduling info on the session row (US-AG-01)."""
    db = _db()
    if not db or not session_id:
        return
    try:
        db.table("sessions").update({
            "candidate_name": analysis.get("candidateName"),
            "candidate_email": analysis.get("candidateEmail"),
            "role": analysis.get("jobRole"),
            "detected_level": analysis.get("detectedLevel"),
            "level_reason": analysis.get("levelReason"),
            "key_skills": analysis.get("skills"),
            "missing_skills": analysis.get("missingSkills"),
            "technical_stack": analysis.get("technicalStack"),
            "jd_match_score": analysis.get("jdMatchScore"),
            "analysis_summary": analysis.get("analysisSummary"),
            "meeting_url": meeting_url, "scheduled_at": scheduled_for_iso,
            "jd_text": jd_text, "resume_text": resume_text,
        }).eq("id", session_id).execute()
    except Exception as e:
        print(f"[ERROR] update_session_analysis() failed: {e}")


def save_questions(session_id, questions: list) -> None:
    """Persist the generated dynamic question plan (US-AG-02)."""
    db = _db()
    if not db or not session_id:
        return
    try:
        rows = [{
            "session_id": session_id, "question_number": i + 1,
            "question_text": q.get("question"), "topic": q.get("topic"),
            "question_type": q.get("question_type"), "depth": q.get("depth"),
            "target_skill": q.get("target_skill"), "key_concepts": q.get("key_concepts", []),
            "status": "pending",
        } for i, q in enumerate(questions)]
        if rows:
            db.table("questions").insert(rows).execute()
    except Exception as e:
        print(f"[ERROR] save_questions() failed: {e}")


def get_questions(session_id) -> list:
    """Read the question plan for a session, ordered (for the interview engine to use)."""
    db = _db()
    if not db or not session_id:
        return []
    try:
        res = (db.table("questions").select("*").eq("session_id", session_id)
               .order("question_number").execute())
        return res.data or []
    except Exception as e:
        print(f"[ERROR] get_questions() failed: {e}")
        return []


def list_sessions_with_reports() -> list:
    """
    Dashboard list, shaped for their frontend:
    adds recommendation/overall_score, selection_status (their SessionsTab filter field),
    and created_at alias (their components read created_at; our column is started_at).
    """
    db = _db()
    if not db:
        return []
    try:
        sess = (db.table("sessions").select("*").order("started_at", desc=True).execute()).data or []
        reps = (db.table("reports").select("session_id, recommendation, overall_score").execute()).data or []
        rep_map = {r["session_id"]: r for r in reps}
        for s in sess:
            r = rep_map.get(s["id"])
            s["recommendation"] = r.get("recommendation") if r else None
            s["overall_score"] = r.get("overall_score") if r else None
            s["selection_status"] = s["recommendation"] or "N/A"          # their filter field
            s.setdefault("created_at", s.get("started_at"))               # their time field
        return sess
    except Exception as e:
        print(f"[ERROR] list_sessions_with_reports() failed: {e}")
        return []


def _pair_transcript(rows: list, per_topic: list) -> list:
    """
    Their ReportsTab expects paired Q&A: {question_text, answer_text, overall_score,
    evaluation_note}. Our answers table stores transcript ROWS (one per utterance),
    so pair question→answer by q_id and attach the per-topic score by topic.
    """
    topic_scores = {t.get("topic"): t for t in (per_topic or []) if isinstance(t, dict)}
    pairs, by_qid = [], {}
    for r in rows:
        qid = r.get("q_id")
        if not qid or qid in ("intro", "closing"):
            continue
        slot = by_qid.setdefault(qid, {"q_id": qid, "topic": r.get("topic")})
        if r.get("role") in ("question", "followup_question"):
            slot["question_text"] = r.get("text")
        elif r.get("role") in ("answer", "followup_answer"):
            slot["answer_text"] = r.get("text")
            slot["evaluation_note"] = r.get("category")
    for qid in sorted(by_qid, key=lambda k: [int(p) if p.isdigit() else 0 for p in str(k).split(".")]):
        slot = by_qid[qid]
        if not slot.get("question_text") and not slot.get("answer_text"):
            continue
        ts = topic_scores.get(slot.get("topic"), {})
        slot["overall_score"] = ts.get("topic_score")
        if ts.get("note"):
            slot["evaluation_note"] = ts["note"]
        pairs.append(slot)
    return pairs


def get_session_full(session_id) -> dict:
    """
    Full session detail in the NESTED shape their frontend consumes:
      {session: {...}, questions: [...], answers: [paired Q&A], report: {...}}
    (SessionsTab reads .questions for the plan modal; ReportsTab reads .session/.report/.answers)
    """
    db = _db()
    if not db or not session_id:
        return {}
    try:
        s = db.table("sessions").select("*").eq("id", session_id).execute()
        session = s.data[0] if s.data else {}
        session.setdefault("created_at", session.get("started_at"))
        report = get_report(session_id)
        return {
            "session": session,
            "questions": get_questions(session_id),
            "answers": _pair_transcript(read_answers(session_id), report.get("per_topic")),
            "report": report or None,
        }
    except Exception as e:
        print(f"[ERROR] get_session_full() failed: {e}")
        return {}


def get_report(session_id) -> dict:
    """Read the report row for a session."""
    db = _db()
    if not db or not session_id:
        return {}
    try:
        res = db.table("reports").select("*").eq("session_id", session_id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        print(f"[ERROR] get_report() failed: {e}")
        return {}