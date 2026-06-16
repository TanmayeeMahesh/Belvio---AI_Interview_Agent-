#!/usr/bin/env python
"""
test_production.py — Full production flow test (simulates what the UI sends).

What this does:
  1. Signs in to Supabase → gets JWT
  2. POST /api/analyse  (JD + resume)  x2 candidates
  3. POST /api/schedule (generates questions, saves to DB, emails invite, schedules bot)  x2
  4. Polls GET / until both bots appear as active_interviews = 2
  5. Prints session IDs so you can check reports after

BEFORE RUNNING:
  - Start ngrok:        ngrok http 8000
  - Update NGROK_URL in .env if it changed
  - Start server:       python app_full.py
  - Fill in CONFIG below (PDFs, meeting URLs, candidate emails)
  - Have both meeting tabs open in browser, ready to admit the bots
"""

import os, sys, time, requests
from dotenv import load_dotenv

load_dotenv()

SERVER   = "http://localhost:8000"
SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_KEY")

# ═══════════════════════════════════════════════════════════
#  CONFIG — fill these in before running
# ═══════════════════════════════════════════════════════════

SUPABASE_EMAIL    = "2023tanmayee.km@vidyashilp.edu.in"   # your Supabase login email
SUPABASE_PASSWORD = "bella@2026"            # your Supabase login password

CANDIDATE_1 = {
    "resume_pdf":  r"C:\Users\Lenovo\Interview-bot\KHUSHI_VERMA_RESUME (2).pdf",
    "jd_pdf":      r"Business_Analyst_JD_MNR.pdf",          # can be same JD for both
    "role":        "business analyst",                        # role to analyze against
    "email":       "khushiverma0819@gmail.com",
    "meeting_url": "https://teams.microsoft.com/meet/49797629510105?p=6j8HoPHyzHRkdK82mK",  # bot joins THIS meeting
}

CANDIDATE_2 = {
    "resume_pdf":  r"C:\Users\Lenovo\Interview-bot\MehakTangraik_Resume.pdf",
    "jd_pdf":      r"C:\Users\Lenovo\Interview-bot\Frontend_Developer_JD.pdf",
    "role":        "frontend developer",
    "email":       "tangraikmehak@gmail.com",
    "meeting_url": "https://meet.google.com/stv-pyzc-dfc",  # DIFFERENT meeting link
}

DELAY_MINUTES = 2    # bots join in 2 minutes — have both meetings open NOW before running

# ═══════════════════════════════════════════════════════════

def sign_in():
    print("🔐 Signing in to Supabase...")
    try:
        from supabase import create_client
        sb = create_client(SUPA_URL, SUPA_KEY)
        res = sb.auth.sign_in_with_password({"email": SUPABASE_EMAIL, "password": SUPABASE_PASSWORD})
        token = res.session.access_token
        print(f"✅ Signed in as {SUPABASE_EMAIL}")
        return token
    except Exception as e:
        print(f"❌ Sign-in failed: {e}")
        print("   → Make sure you have a user account in Supabase Auth.")
        print("   → Create one at: your Supabase project → Authentication → Users → Add user")
        sys.exit(1)

def analyse(token, cand, label):
    print(f"\n📄 [{label}] Analysing {cand['role']}...")
    headers = {"authorization": f"Bearer {token}"}
    with open(cand["resume_pdf"], "rb") as r, open(cand["jd_pdf"], "rb") as j:
        resp = requests.post(
            f"{SERVER}/api/analyse",
            headers=headers,
            files={
                "resume": (os.path.basename(cand["resume_pdf"]), r, "application/pdf"),
                "jd":     (os.path.basename(cand["jd_pdf"]),     j, "application/pdf"),
            },
            data={"role": cand["role"]},
        )
    if resp.status_code != 200:
        print(f"❌ /api/analyse failed: {resp.status_code} — {resp.text[:200]}")
        sys.exit(1)
    result = resp.json()
    a = result["analysis"]
    print(f"   ✅ Name:      {a.get('candidateName')}")
    print(f"   ✅ Level:     {a.get('detectedLevel')}  ({a.get('levelReason','')})")
    print(f"   ✅ JD match:  {a.get('jdMatchScore')}%")
    print(f"   ✅ Skills:    {', '.join((a.get('skills') or [])[:5])}")
    print(f"   ✅ Missing:   {', '.join((a.get('missingSkills') or [])[:3])}")
    return result

def schedule(token, analysis_result, cand, label):
    print(f"\n🗓️  [{label}] Scheduling (bot joins in {DELAY_MINUTES} min)...")
    headers = {"authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "analysis":          analysis_result["analysis"],
        "tempFiles":         analysis_result["tempFiles"],
        "role":              cand["role"],
        "questionCount":     12,
        "confirmedEmail":    cand["email"],
        "manualMeetingLink": cand["meeting_url"],
        "delayMinutes":      DELAY_MINUTES,
    }
    resp = requests.post(f"{SERVER}/api/schedule", headers=headers, json=body)
    if resp.status_code != 200:
        print(f"❌ /api/schedule failed: {resp.status_code} — {resp.text[:200]}")
        sys.exit(1)
    result = resp.json()
    print(f"   ✅ session_id:         {result['session_id']}")
    print(f"   ✅ questions_generated: {result['questions_generated']}")
    print(f"   ✅ email_sent:          {result['email_sent']}")
    print(f"   ✅ bot joins at:        {result['scheduled_at']} UTC")
    return result

def poll_until_live(s1, s2):
    print(f"\n{'='*55}")
    print(f"  JOIN YOUR MEETINGS NOW — bots arrive in ~{DELAY_MINUTES} min")
    print(f"  Meeting 1: {CANDIDATE_1['meeting_url']}")
    print(f"  Meeting 2: {CANDIDATE_2['meeting_url']}")
    print(f"{'='*55}\n")
    print("Polling server every 10s...\n")

    start = time.time()
    timeout = DELAY_MINUTES * 60 + 120   # delay + 2 min grace
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{SERVER}/").json()
            count = r.get("active_interviews", 0)
            bots  = r.get("bots", [])
            elapsed = int(time.time() - start)
            print(f"  [{elapsed:>3}s] active_interviews={count}  bots={[b[:8] for b in bots]}")
            if count >= 2:
                print("\n🎉 Both bots are live simultaneously!")
                print(f"   Bot 1 session: {s1['session_id']}")
                print(f"   Bot 2 session: {s2['session_id']}")
                print("\nSay 'yes' in both meetings to start interviews.")
                print("\nAfter both interviews finish, check reports:")
                print(f"   GET http://localhost:8000/api/hr/report/{s1['session_id']}")
                print(f"   GET http://localhost:8000/api/hr/report/{s2['session_id']}")
                print(f"   GET http://localhost:8000/api/hr/report/{s1['session_id']}/pdf")
                print(f"   GET http://localhost:8000/api/hr/report/{s2['session_id']}/pdf")
                return
        except Exception as e:
            print(f"   server not reachable: {e}")
        time.sleep(10)
    print("⏰ Timeout — bots didn't show up. Check server logs.")

if __name__ == "__main__":
    # Preflight check
    try:
        requests.get(SERVER, timeout=3)
    except Exception:
        print(f"❌ Server not running at {SERVER}. Start it first: python app_full.py")
        sys.exit(1)

    token = sign_in()

    a1 = analyse(token, CANDIDATE_1, "Candidate 1")
    s1 = schedule(token, a1, CANDIDATE_1, "Candidate 1")

    a2 = analyse(token, CANDIDATE_2, "Candidate 2")
    s2 = schedule(token, a2, CANDIDATE_2, "Candidate 2")

    poll_until_live(s1, s2)
