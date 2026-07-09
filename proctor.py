"""
proctor.py — Post-interview INTEGRITY analysis (Mode A). Fail-safe, runs in a background thread.

Two independent signals, both FLAGS FOR HUMAN REVIEW (never verdicts):
  1. TRANSCRIPT AUTHENTICITY (text, Groq) — answers that read like AI text read aloud.
  2. VIDEO (opencv + MediaPipe locally, Gemini→OpenAI vision on sparse frames) — face presence,
     second person, camera off, phone visible. The heavy CV libs are imported LAZILY inside the video
     function, so app boot never depends on them and any import issue only degrades proctoring.

Design rules:
  - NEVER raises into the caller — any failure saves {assessed: false}/partial and returns.
  - Decoupled integrity_reports table (no write race with the evaluator).
  - Transcript result is saved immediately; the slower video result updates the row when ready.
"""
import os, json, time, base64, threading, requests
from groq import Groq
from dotenv import load_dotenv
import db

load_dotenv()

_PROCTOR_MODEL = "llama-3.3-70b-versatile"   # text reasoning; runs in background, latency hidden
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Video sampling — env-tunable. Cloud calls are kept SPARSE for cost control.
_FRAME_SEC  = int(os.getenv("PROCTOR_FRAME_SEC", "10"))   # local MediaPipe face-sample interval (s)
_CLOUD_SEC  = int(os.getenv("PROCTOR_CLOUD_SEC", "60"))   # cloud vision (phone/2nd-person) interval (s)
_VIDEO_WAIT = int(os.getenv("PROCTOR_VIDEO_WAIT", "20"))  # poll attempts for the video URL (×30s = 10 min)
_NOFACE_EVENT_FRAMES = 2                                  # ≥N consecutive missing-face samples → one event
_video_lock = threading.Lock()   # serialize video analysis (avoid CPU contention on the 2-vCPU tier)

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
    prompt = f"""You are checking whether interview answers were likely READ from AI-generated text
(e.g. ChatGPT/Gemini) rather than spoken spontaneously. Input is speech-to-text, so written formatting
is lost — judge by CONTENT PATTERNS, not formatting. This is a soft signal for human review: balance
the two errors — don't falsely accuse honest candidates, but DO surface answers with the hallmarks of
read-aloud AI text.

NOT evidence on their own (these are normal human speech):
- being articulate, fluent, confident, or using good vocabulary
- a correct answer; formal phrasing; non-native English phrasing
- absence of "um"/"uh" (speech-to-text strips those)

HALLMARKS of read-aloud AI text — weigh how MANY appear together, across answers:
- comprehensive, textbook-style coverage that cleanly names AND defines every relevant concept
- sustained essay structure in a spoken answer ("firstly… secondly…", tidy enumerated points)
- polished complete sentences with NO spontaneous-speech markers at all — no self-correction, no
  restarts, no "I think/I guess", no tangents, and no personal specifics or anecdotes
- register reads like written prose rather than conversation
- explicit AI artifacts: "as an AI language model", "here are N points/ways", "in summary,"

Scoring:
- low    = reads like real speech (some spontaneity, personal specifics, small imperfections)
- medium = one or two answers show SEVERAL hallmarks together (esp. comprehensive + zero spontaneity)
- high   = most answers show the hallmarks, OR any explicit AI artifact appears
Genuine human answers almost always carry personal specifics or small imperfections — their COMPLETE
absence across polished, textbook-comprehensive answers is the main signal. When truly balanced between
low and medium, pick medium only if spontaneity markers are entirely absent.

Only list an answer in flagged_answers if it shows the hallmarks; cite the specific pattern.

TRANSCRIPT:
{transcript}

Reply ONLY valid JSON, no markdown:
{{"ai_likelihood":"low|medium|high",
"flagged_answers":[{{"topic":"<topic>","reason":"<the specific pattern, <=12 words>"}}]}}"""
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


# ─────────────────────────── VIDEO ANALYSIS (Mode A) ───────────────────────────
def _fmt(sec):
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _parse_cloud(text):
    """Parse the vision model's JSON reply → {'people': int, 'phone': bool} or None."""
    import re
    try:
        raw = (text or "").strip().replace("```json", "").replace("```", "").strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        d = json.loads(m.group(0) if m else raw)
        return {"people": int(d.get("people", 1)), "phone": bool(d.get("phone", False))}
    except Exception:
        return None


def _cloud_vision(jpeg_bytes):
    """Ask a vision model about ONE frame: how many people + is a phone visible. Gemini→OpenAI. None on failure."""
    prompt = ("This is a webcam frame from a candidate in an online interview. Reply ONLY with JSON: "
              '{"people": <number of distinct human faces visible>, "phone": <true only if a mobile '
              'phone is clearly visible>}. Be conservative — if unsure, use people 1 and phone false.')
    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-flash-latest")   # 2.0-flash was retired 2026-06-01; alias survives future retirements
            resp = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": jpeg_bytes}])
            parsed = _parse_cloud(resp.text)
            if parsed:
                return parsed
        except Exception as e:
            print(f"[PROCTOR] gemini vision failed: {e}")
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            b64 = base64.b64encode(jpeg_bytes).decode()
            resp = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
                model="gpt-4o-mini", max_tokens=60,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
            return _parse_cloud(resp.choices[0].message.content)
        except Exception as e:
            print(f"[PROCTOR] openai vision failed: {e}")
    return None


def _dedupe_events(events, per_type=8, total=25):
    """Dedupe by (type, at) and cap PER TYPE so a noisy minor type can't evict significant ones."""
    seen, counts, out = set(), {}, []
    for e in events:
        key = (e.get("type"), e.get("at"))
        if key in seen:
            continue
        typ = e.get("type")
        if counts.get(typ, 0) >= per_type:
            continue
        seen.add(key)
        counts[typ] = counts.get(typ, 0) + 1
        out.append(e)
    return out[:total]


def _scan_video(cv2, mp, path):
    """Sample frames, run MediaPipe face detection + sparse cloud vision, aggregate integrity signals."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return {"assessed": False, "note": "could not open video"}
    # OpenCV 5.x returns -1 (not 0) for unavailable properties → guard with > 0, not falsiness
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 0 else 25.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    frame_count = frame_count if frame_count and frame_count > 0 else 0
    duration = (frame_count / fps) if frame_count else 0
    if duration <= 0:
        cap.release()
        return {"assessed": False, "note": "empty/zero-length video"}

    face_frames = sampled = no_face_run = multi_run = fails = 0
    no_face_start = multi_start = None
    events, last_cloud_t = [], -_CLOUD_SEC
    mp_fd = mp.solutions.face_detection
    try:
        with mp_fd.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
            t = 0.0
            while t < duration:
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, frame = cap.read()
                if not ok:
                    fails += 1
                    if fails >= 3:                 # a few consecutive seek/read failures → stop
                        break
                    t += _FRAME_SEC
                    continue
                fails = 0
                at = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0   # actual decoded time (keyframe-accurate)
                if at <= 0:
                    at = t
                sampled += 1
                res = fd.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                n_faces = len(res.detections) if res.detections else 0

                # ── face presence (run-aggregated) ──
                if n_faces >= 1:
                    face_frames += 1
                    if no_face_run >= _NOFACE_EVENT_FRAMES and no_face_start is not None:
                        events.append({"type": "no_face", "at": _fmt(no_face_start),
                                       "duration_s": max(0, int(at - no_face_start))})
                    no_face_run, no_face_start = 0, None
                else:
                    if no_face_run == 0:
                        no_face_start = at
                    no_face_run += 1

                # ── multiple faces (run-aggregated so it can't flood the event list) ──
                if n_faces >= 2:
                    if multi_run == 0:
                        multi_start = at
                    multi_run += 1
                else:
                    if multi_run >= 1 and multi_start is not None:
                        events.append({"type": "multiple_faces", "at": _fmt(multi_start),
                                       "duration_s": max(0, int(at - multi_start))})
                    multi_run, multi_start = 0, None

                # ── sparse cloud check: phone / second person ──
                if (GEMINI_API_KEY or OPENAI_API_KEY) and (at - last_cloud_t) >= _CLOUD_SEC:
                    last_cloud_t = at
                    ok2, jpg = cv2.imencode(".jpg", frame)
                    if ok2:
                        cvres = _cloud_vision(jpg.tobytes())
                        if cvres and cvres.get("phone"):
                            events.append({"type": "phone_visible", "at": _fmt(at)})
                        if cvres and cvres.get("people", 1) >= 2:
                            events.append({"type": "second_person", "at": _fmt(at)})
                t += _FRAME_SEC
    finally:
        cap.release()

    if sampled == 0:
        return {"assessed": False, "note": "no frames sampled"}
    # flush trailing runs
    if no_face_run >= _NOFACE_EVENT_FRAMES and no_face_start is not None:
        events.append({"type": "no_face", "at": _fmt(no_face_start),
                       "duration_s": max(0, int(duration - no_face_start))})
    if multi_run >= 1 and multi_start is not None:
        events.append({"type": "multiple_faces", "at": _fmt(multi_start),
                       "duration_s": max(0, int(duration - multi_start))})
    face_pct = round(100 * face_frames / sampled)
    return {
        "assessed": True,
        "face_present_pct": face_pct,
        "camera_off": face_pct < 20,          # essentially never saw a face
        "sampled_frames": sampled,
        "event_types": sorted({e.get("type") for e in events}),  # FULL set → flag is truncation-proof
        "events": _dedupe_events(events),                        # capped list for display
    }


def analyze_video(bot_id):
    """Download the candidate's video from Recall and scan it. Fail-safe. Only the CPU-bound scan is
    serialized — the I/O (polling + download) runs OUTSIDE the lock so parallel sessions don't block on it."""
    if not bot_id:
        return {"assessed": False, "note": "no bot_id"}
    try:
        import cv2, tempfile               # lazy: app boot never depends on these
        import mediapipe as mp
    except Exception as e:
        return {"assessed": False, "note": f"cv libraries unavailable: {e}"}
    import app_full                          # lazy: avoids circular import at load time
    # poll for the video URL (I/O — outside the lock; recording takes minutes to process)
    url = None
    for _ in range(_VIDEO_WAIT):
        url = app_full.get_fresh_recording_url(bot_id, "video")
        if url:
            break
        time.sleep(30)
    if not url:
        return {"assessed": False, "note": "video recording not available"}
    # download to a temp file created atomically (I/O — outside the lock)
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
        with _video_lock:                    # serialize ONLY the CPU-bound scan (2-vCPU tier)
            return _scan_video(cv2, mp, path)
    except Exception as e:
        return {"assessed": False, "note": f"video analysis failed: {e}"}
    finally:
        try:
            os.remove(path)                  # data minimization: don't keep the video
        except Exception:
            pass


# ─────────────────────────── FLAG COMBINATION ───────────────────────────
_SEV = {"clean": 0, "minor": 1, "significant": 2}

def _transcript_flag(ta):
    lvl = (ta or {}).get("ai_likelihood", "low")
    return {"high": "significant", "medium": "minor"}.get(lvl, "clean")

def _video_flag(video):
    if not video or not video.get("assessed"):
        return "clean"   # not assessed adds no flag
    # prefer the full event_types set (truncation-proof); fall back to the displayed events
    vtypes = set(video.get("event_types") or [e.get("type") for e in video.get("events", [])])
    if video.get("camera_off") or "second_person" in vtypes or "phone_visible" in vtypes:
        return "significant"
    if "no_face" in vtypes or "multiple_faces" in vtypes:
        return "minor"
    return "clean"

def _combine(*flags):
    worst = max((_SEV.get(f, 0) for f in flags), default=0)
    return {0: "clean", 1: "minor", 2: "significant"}[worst]


def _summary(flag, ta, video):
    bits = []
    n = len((ta or {}).get("flagged_answers", []))
    if n:
        bits.append(f"{n} answer(s) possibly AI-assisted ({(ta or {}).get('ai_likelihood')})")
    if video and video.get("assessed"):
        vtypes = {e.get("type") for e in video.get("events", [])}
        if video.get("camera_off"):
            bits.append("camera off / face rarely visible")
        if "second_person" in vtypes:
            bits.append("a second person appeared on camera")
        if "phone_visible" in vtypes:
            bits.append("a phone was visible")
        if "no_face" in vtypes and not video.get("camera_off"):
            bits.append("candidate left the frame")
    if not bits:
        if video and not video.get("assessed"):
            return "No transcript concerns. Video analysis pending or unavailable."
        return "No integrity concerns detected."
    s = "; ".join(bits)
    return s[:1].upper() + s[1:] + " — review recommended."


def analyze_session(session_id, bot_id=None):
    """
    MAIN ENTRY — runs post-interview in a daemon thread. Fail-safe: never raises.
    Saves the fast transcript result immediately, then updates the row once the slower video
    analysis (poll for URL → download → scan) completes.
    """
    # 1) transcript signal (fast) — save right away so the dashboard shows something quickly
    try:
        ta = analyze_transcript_authenticity(session_id)
    except Exception as e:
        print(f"[PROCTOR] transcript failed: {e}")
        ta = {"ai_likelihood": "unknown", "flagged_answers": []}
    ta_flag = _transcript_flag(ta)
    db.save_integrity_report(session_id, {
        "assessed": True, "integrity_flag": ta_flag,
        "transcript_authenticity": ta,
        "video": {"assessed": False, "note": "analysing video…"},
        "summary": _summary(ta_flag, ta, None),
    })
    print(f"[PROCTOR] {session_id} transcript → {ta_flag}")

    # 2) video signal (slow) — then update the row with the combined result
    try:
        video = analyze_video(bot_id)
    except Exception as e:
        print(f"[PROCTOR] video failed: {e}")
        video = {"assessed": False, "note": f"video error: {e}"}
    flag = _combine(ta_flag, _video_flag(video))
    db.save_integrity_report(session_id, {
        "assessed": True, "integrity_flag": flag,
        "transcript_authenticity": ta, "video": video,
        "summary": _summary(flag, ta, video),
    })
    print(f"[PROCTOR] {session_id} → {flag} (transcript={ta_flag}, video={_video_flag(video)})")
