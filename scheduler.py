"""
scheduler.py — Candidate invitation + (optional) meeting creation.

Two independent pieces:
  1. send_invite()        — emails the meeting link to the candidate via Gmail SMTP. NEEDS NOTHING
                            from Microsoft. Works in every scheduling path. READY NOW.
  2. create_google_meet() — creates a Google Calendar event WITH a Meet link via the Google
                            Calendar API. Sidesteps the Microsoft admin-consent wall. GATED on
                            Google OAuth setup (credentials.json + first-run browser consent).

Action A (create the link) is the only part that's ever blocked. Action B (email it) never is.
"""
import os, smtplib, ssl
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# ─── Gmail SMTP config (.env) ─────────────────────────────
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")        # e.g. aiinterviewbot@gmail.com
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")   # 16-char App Password, NOT your login password


# ─── 1. EMAIL INVITE (ready now, no Microsoft/Google needed) ──────────────
def send_invite(to_email: str, candidate_name: str, meeting_url: str,
                role: str = None, when: str = None) -> bool:
    """
    Email the interview invite + meeting link to the candidate.
    Works regardless of how the meeting link was created (Teams by hand, Meet by API, etc).
    Returns True on success, False on failure (fail-safe — never crashes the caller).
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("❌ send_invite: GMAIL_ADDRESS / GMAIL_APP_PASSWORD missing in .env")
        return False
    if not to_email:
        print("❌ send_invite: no candidate email (resume parsing may have failed)")
        return False

    name = candidate_name or "Candidate"
    role_line = f" for the {role} position" if role else ""
    when_line = f"\n\nScheduled time: {when}" if when else ""

    body = (
        f"Hello {name},\n\n"
        f"You're invited to an AI-conducted technical interview{role_line}. "
        f"The session is conducted by an AI interviewer and will be recorded (audio and video) "
        f"and transcribed for evaluation.{when_line}\n\n"
        f"Join using this link at your scheduled time:\n{meeting_url}\n\n"
        f"Please join from a quiet space with a working microphone. When the AI interviewer asks "
        f"for your consent at the start, please respond verbally to begin.\n\n"
        f"Best regards,\nRecruitment Team"
    )

    msg = EmailMessage()
    msg["Subject"] = f"Your Interview Invitation{role_line}"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_email
    msg.set_content(body)

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"📧 Invite sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ send_invite failed: {e}")
        return False


# ─── 2. GOOGLE MEET CREATION (gated on OAuth setup) ───────────────────────
# Setup required before this runs:
#   pip install google-auth google-auth-oauthlib google-api-python-client
#   1. Google Cloud Console → new project → enable "Google Calendar API"
#   2. Create OAuth client ID (Desktop app) → download as credentials.json (place beside this file)
#   3. First run opens a browser to authorize; token is cached as token.json after that
# No org-admin consent needed (unlike Microsoft Teams) — ordinary Google account works.

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

def create_google_meet(subject: str, start_iso: str, end_iso: str,
                       candidate_email: str = None) -> str | None:
    """
    Create a Google Calendar event with a Meet link. Returns the Meet join URL or None.
    start_iso / end_iso: RFC3339, e.g. "2026-06-10T10:00:00+05:30".
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ create_google_meet: run "
              "pip install google-auth google-auth-oauthlib google-api-python-client")
        return None

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GOOGLE_SCOPES)
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists("credentials.json"):
                    print("❌ create_google_meet: credentials.json missing (see setup notes)")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)   # opens browser once
            with open("token.json", "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"❌ create_google_meet auth failed: {e}")
            return None

    try:
        service = build("calendar", "v3", credentials=creds)
        event = {
            "summary": subject,
            "start": {"dateTime": start_iso},
            "end":   {"dateTime": end_iso},
            "conferenceData": {"createRequest": {
                "requestId": f"meet-{abs(hash(subject + start_iso))}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }},
        }
        if candidate_email:
            event["attendees"] = [{"email": candidate_email}]
        created = service.events().insert(
            calendarId="primary", body=event,
            conferenceDataVersion=1, sendUpdates="all").execute()
        link = created.get("hangoutLink")
        print(f"🎥 Google Meet created: {link}")
        return link
    except Exception as e:
        print(f"❌ create_google_meet failed: {e}")
        return None