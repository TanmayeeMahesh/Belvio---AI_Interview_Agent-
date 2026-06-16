"""
test_extraction.py — replicates the EXACT production pipeline (US-AG-01 + US-AG-02)
without needing the frontend or an HTTP call.

Shows you:
  STAGE 1  what text was pulled from each PDF
  STAGE 2  the full analysis JSON + the exact `sessions` row that would be stored
  STAGE 3  every generated question + the exact `questions` rows + a difficulty audit

Usage (PowerShell, venv active):
  python test_extraction.py jd.pdf resume.pdf                       # dry run (no DB writes)
  python test_extraction.py jd.pdf resume.pdf "Backend Engineer" 12 # role + question count
  python test_extraction.py jd.pdf resume.pdf "Backend Engineer" 12 --save   # ALSO writes to Supabase
"""
import sys, json
import extraction

# ─── args ────────────────────────────────────────────────────────────────────
args = [a for a in sys.argv[1:] if a != "--save"]
SAVE = "--save" in sys.argv
if len(args) < 2:
    print(__doc__); sys.exit(1)
jd_path, resume_path = args[0], args[1]
role  = args[2] if len(args) > 2 else "Software Engineer"
count = int(args[3]) if len(args) > 3 else 12

DIV = "═" * 70

# ─── STAGE 1: PDF text extraction (what api_routes does on upload) ──────────
print(f"\n{DIV}\nSTAGE 1 — PDF TEXT EXTRACTION\n{DIV}")
jd_text     = extraction.extract_text(jd_path)
resume_text = extraction.extract_text(resume_path)
for label, text in [("JD", jd_text), ("RESUME", resume_text)]:
    print(f"\n[{label}] {len(text)} chars extracted. First 300:")
    print("  " + text[:300].replace("\n", " ") + " ...")
    if len(text) < 100:
        print(f"  🚩 WARNING: {label} text is suspiciously short — scanned/image PDF? (US-HR AC-05)")

# ─── STAGE 2: LLM analysis (exact /api/analyse call) ─────────────────────────
print(f"\n{DIV}\nSTAGE 2 — DOCUMENT ANALYSIS  (analyze_documents(jd, resume, role))\n{DIV}")
analysis = extraction.analyze_documents(jd_text, resume_text, role)
print("\nFULL ANALYSIS JSON (everything the LLM extracted):")
print(json.dumps(analysis, indent=2))

# the exact sessions-row mapping from db.update_session_analysis()
session_row = {
    "candidate_name":   analysis.get("candidateName"),
    "candidate_email":  analysis.get("candidateEmail"),
    "role":             analysis.get("jobRole"),
    "detected_level":   analysis.get("detectedLevel"),
    "level_reason":     analysis.get("levelReason"),
    "key_skills":       analysis.get("skills"),
    "missing_skills":   analysis.get("missingSkills"),
    "technical_stack":  analysis.get("technicalStack"),
    "jd_match_score":   analysis.get("jdMatchScore"),
    "analysis_summary": analysis.get("analysisSummary"),
    "jd_text":          f"<{len(jd_text)} chars>",
    "resume_text":      f"<{len(resume_text)} chars>",
}
print("\nWHAT GETS STORED in the `sessions` row (db.update_session_analysis):")
for k, v in session_row.items():
    print(f"  {k:18} = {v}")
missing = [k for k, v in session_row.items() if v in (None, [], "")]
if missing:
    print(f"\n🚩 Fields the LLM left empty (check if the PDFs actually contain them): {missing}")

# ─── STAGE 3: question generation (exact /api/schedule call) ─────────────────
print(f"\n{DIV}\nSTAGE 3 — QUESTION PLAN  (generate_question_plan(analysis, role, {count}))\n{DIV}")
qs = extraction.generate_question_plan(analysis, role, count)
print(f"\n{len(qs)} questions generated:\n")
for i, q in enumerate(qs, 1):
    print(f"Q{i} [{q.get('depth','?'):7}] [{q.get('question_type','?'):12}] topic={q.get('topic')}")
    print(f"    {q.get('question')}")
    print(f"    target_skill: {q.get('target_skill')}  |  key_concepts: {q.get('key_concepts')}\n")

print("WHAT GETS STORED in `questions` rows (db.save_questions) — one row per Q:")
print("  session_id | question_number | question_text | topic | question_type | depth | target_skill | key_concepts | status='pending'")

# ─── difficulty-to-source audit (your rule) ──────────────────────────────────
print(f"\n{DIV}\nDIFFICULTY-TO-SOURCE AUDIT\n{DIV}")
by_depth = {}
for q in qs:
    by_depth.setdefault(q.get("depth", "?"), []).append(q)
for d in ("surface", "medium", "deep"):
    print(f"  {d:7}: {len(by_depth.get(d, []))} questions")

miss_skills = [s.lower() for s in (analysis.get("missingSkills") or [])]
deep_qs = by_depth.get("deep", [])
hits = sum(1 for q in deep_qs
           if any(m in (q.get("question", "") + " " + str(q.get("target_skill", ""))).lower()
                  for m in miss_skills))
if deep_qs:
    print(f"\n  deep questions referencing a JD-gap skill: {hits}/{len(deep_qs)}")
    if miss_skills and hits == 0:
        print("  🚩 No deep question targets the JD gaps — prompt may need another pass. Show me this output.")
else:
    print("  🚩 No 'deep' questions generated at all — show me this output.")

# ─── optional: actually persist (replicates /api/schedule writes) ────────────
if SAVE:
    import db
    print(f"\n{DIV}\nSAVING TO SUPABASE\n{DIV}")
    sid = db.create_session(None, len(qs), analysis.get("candidateName"),
                            analysis.get("candidateEmail"), role, status="scheduled")
    db.update_session_analysis(sid, analysis, meeting_url=None,
                               scheduled_for_iso=None, jd_text=jd_text, resume_text=resume_text)
    db.save_questions(sid, qs)
    print(f"\n✅ session_id = {sid}")
    print(f"   Check Supabase: sessions + questions tables.")
    print(f"   Live-test with: http://127.0.0.1:8000/trigger-bot?meeting_url=YOUR_LINK&session_id={sid}")
else:
    print(f"\n(dry run — nothing written to DB. Re-run with --save to persist.)")