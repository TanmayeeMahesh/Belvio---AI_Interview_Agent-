"""
api_routes.py — HR-facing API matching the other team's frontend contract.

Their React dashboard calls these (via axios at localhost:8000):
  POST /api/analyse            multipart: resume, jd, role  → {analysis, tempFiles}
  POST /api/schedule           json: {analysis, role, questionCount, confirmedEmail,
                                      manualMeetingLink, meetingPlatform} → {scheduled_at, ...}
  GET  /api/hr/sessions        → [{id, candidate_name, role, status, scheduled_at, created_at}]
  GET  /api/hr/session/{id}    → full session detail
  GET  /api/hr/report/{id}     → report row
  GET  /api/hr/report/{id}/pdf → the generated PDF (download)
  GET  /api/keys               → masked per-user API keys (sidebar)
  POST /api/keys               json: {gemini, claude, groq} → store encrypted

Wires together: extraction (US-AG-01/02), scheduler (invite+schedule), auth (login/keys),
report_pdf (US-AG-08 AC-06), and our Supabase via db.py.
"""
import os, uuid, json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, UploadFile, File, Form, Request, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse

import db, extraction, scheduler, auth, report_pdf, evaluator
from supabase import create_client as _supa_create
import os as _os
from pydantic import BaseModel
from fastapi import Header, HTTPException

router = APIRouter()

UPLOAD_DIR = os.path.join("uploads", "documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)




from pydantic import BaseModel

class CheckEmailRequest(BaseModel):
    email: str

class CompleteRegistrationRequest(BaseModel):
    email: str
    password: str


class CreateOrganizationRequest(BaseModel):
    organization_name: str
    admin_email: str
    
    
class CompleteRegistrationRequest(BaseModel):
    email: str
    password: str    
 
class CreateJobOpeningRequest(BaseModel):
    title: str
    description: str
    when: str
    

class SettingsRequest(BaseModel):
    email_template: str = None
 
class CreateCandidateRequest(BaseModel):
    name: str
    email: str
    role: str
    job_opening_id: str
    
class ScheduleCandidateRequest(BaseModel):
    meeting_url: str
    question_count: int = 12
    delay_minutes: int = 30    
    
    
@router.post("/api/candidates")
async def create_candidate(
    body: CreateCandidateRequest,
    authorization: str = Header(None)
):

    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    result = (
        db._db()
        .table("candidates")
        .insert({
            "name": body.name,
            "email": body.email,
            "role": body.role,
            "job_opening_id": body.job_opening_id,
            "organization_id": org_id
        })
        .execute()
    )

    return result.data[0]

@router.get("/api/candidates")
def list_candidates(
    authorization: str = Header(None)
):

    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    result = (
        db._db()
        .table("candidates")
        .select("*")
        .eq("organization_id", org_id)
        .execute()
    )

    candidates = result.data

    if candidates:
        cand_ids = [c["id"] for c in candidates]
        ints = (
            db._db()
            .table("scheduled_interviews")
            .select("*")
            .in_("candidate_id", cand_ids)
            .execute()
        )
        sched_map = {i["candidate_id"]: i for i in ints.data}

        for c in candidates:
            if c["id"] in sched_map:
                c["is_scheduled"] = True
                c["scheduled_time"] = sched_map[c["id"]].get("scheduled_for")
            else:
                c["is_scheduled"] = False
                c["scheduled_time"] = None

    return candidates


@router.get("/api/job-openings/{job_id}/candidates")
def candidates_for_job(job_id: str):

    result = (
        db._db()
        .table("candidates")
        .select("*")
        .eq("job_opening_id", job_id)
        .execute()
    )

    candidates = result.data

    if candidates:
        cand_ids = [c["id"] for c in candidates]
        ints = (
            db._db()
            .table("scheduled_interviews")
            .select("*")
            .in_("candidate_id", cand_ids)
            .execute()
        )
        sched_map = {i["candidate_id"]: i for i in ints.data}

        for c in candidates:
            if c["id"] in sched_map:
                c["is_scheduled"] = True
                c["scheduled_time"] = sched_map[c["id"]].get("scheduled_for")
            else:
                c["is_scheduled"] = False
                c["scheduled_time"] = None

    return candidates


@router.get("/api/dashboard/org-admin")
def org_admin_dashboard(
    authorization: str = Header(None)
):

    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    hrs = (
        db._db()
        .table("organization_users")
        .select("*", count="exact")
        .eq("role", "HR")
        .eq("organization_id", org_id)
        .execute()
    )

    jobs = (
        db._db()
        .table("job_openings")
        .select("*", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )

    candidates = (
        db._db()
        .table("candidates")
        .select("*", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )

    interviews = (
        db._db()
        .table("scheduled_interviews")
        .select("*", count="exact")
        .eq("organization_id", org_id)
        .execute()
    )

    return {
        "hrs": hrs.count,
        "job_openings": jobs.count,
        "candidates": candidates.count,
        "scheduled_interviews": interviews.count
    }
     
@router.get("/api/dashboard/super-admin")
def super_admin_dashboard():

    organizations = (
        db._db()
        .table("organizations")
        .select("*", count="exact")
        .execute()
    )

    org_admins = (
        db._db()
        .table("organization_users")
        .select("*", count="exact")
        .eq("role", "ORG_ADMIN")
        .execute()
    )

    hrs = (
        db._db()
        .table("organization_users")
        .select("*", count="exact")
        .eq("role", "HR")
        .execute()
    )

    job_openings = (
        db._db()
        .table("job_openings")
        .select("*", count="exact")
        .execute()
    )

    candidates = (
        db._db()
        .table("candidates")
        .select("*", count="exact")
        .execute()
    )

    interviews = (
        db._db()
        .table("scheduled_interviews")
        .select("*", count="exact")
        .execute()
    )

    return {
        "organizations": organizations.count,
        "org_admins": org_admins.count,
        "hrs": hrs.count,
        "job_openings": job_openings.count,
        "candidates": candidates.count,
        "interviews": interviews.count
    }
    
@router.post("/api/job-openings")
async def create_job_opening(
    body: CreateJobOpeningRequest,
    authorization: str = Header(None)
):
    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    result = (
        db._db()
        .table("job_openings")
        .insert({
            "organization_id": org_id,
            "title": body.title,
            "description": body.description,
            "jd_text": body.jd_text,
            "status": "ACTIVE"
        })
        .execute()
    )

    return result.data[0]

@router.get("/api/job-openings")
def list_job_openings(
    authorization: str = Header(None)
):

    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    result = (
        db._db()
        .table("job_openings")
        .select("*")
        .eq("organization_id", org_id)
        .execute()
    )

    return result.data
    
 
    
        
    
@router.post("/api/auth/complete-registration")
async def complete_registration(
    body: CompleteRegistrationRequest
):

    email = body.email.strip().lower()
    password = body.password

    existing = (
        db._db()
        .table("organization_users")
        .select("*")
        .eq("email", email)
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    org_user = existing.data[0]

    if org_user["status"] == "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Account already activated"
        )

    sb = db._db()

    auth_user = sb.auth.sign_up({
        "email": email,
        "password": password
    })
    
    print("AUTH USER =", auth_user)
    print("AUTH USER ID =", auth_user.user.id if auth_user.user else None)

    user_id = auth_user.user.id

    (
        db._db()
        .table("organization_users")
        .update({
            "user_id": user_id,
            "status": "ACTIVE"
        })
        .eq("id", org_user["id"])
        .execute()
    )

    return {
        "message": "Registration completed"
    }
    
 
class CreateHRRequest(BaseModel):
    email: str
    name: str = None
    role: str = "HR"



@router.post("/api/auth/check-email")
async def check_email(body: CheckEmailRequest):

    email = body.email.strip().lower()

    result = (
        db._db()
        .table("organization_users")
        .select("*")
        .eq("email", email)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    user = result.data[0]

    return {
        "exists": True,
        "status": user["status"],
        "role": user["role"]
    }
        
@router.post("/api/org-admin/create-hr")
async def create_hr(
    body: CreateHRRequest,
    authorization: str = Header(None)
):
    user, ctx = _require_context(authorization)

    if ctx["role"] != "ORG_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only ORG_ADMIN can create HRs"
        )

    email = body.email.strip().lower()
    role = body.role.strip().upper() if body.role else "HR"
    if role not in ["HR", "ORG_ADMIN", "RECRUITER", "INTERVIEWER"]:
        role = "HR"

    existing = (
        db._db()
        .table("organization_users")
        .select("*")
        .eq("email", email)
        .execute()
    )

    if existing.data:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    result = (
        db._db()
        .table("organization_users")
        .insert({
            "organization_id": ctx["organization_id"],
            "email": email,
            "name": body.name,
            "role": role,
            "status": "PENDING"
        })
        .execute()
    )

    return result.data[0]            


async def check_email(body: CheckEmailRequest):

    email = body.email.strip().lower()

    result = (
        db._db()
        .table("organization_users")
        .select("*")
        .eq("email", email)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    user = result.data[0]

    return {
        "exists": True,
        "status": user["status"],
        "role": user["role"]
    }
    
        
# ─── AUTH LOGIN ───────────────────────────────────────────
@router.post("/api/auth/login")
async def login(request: Request):
    body = await request.json()
    email    = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required.")
    try:
        sb = _supa_create(_os.getenv("SUPABASE_URL"), _os.getenv("SUPABASE_KEY"))
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        token = res.session.access_token
        return {"token": token, "email": res.user.email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password.")


@router.get("/api/me")
def me(authorization: str = Header(None)):

    user = _require_user(authorization)

    ctx = auth.get_user_context(
        auth.user_id_from(user)
    )

    return {
        "user": user,
        "context": ctx
    }
    
    



@router.get("/api/test-role")
def test_role():

    return auth.get_user_context(
        "da0c3caa-e907-4f1c-8747-e727f608dbd7"
    )


@router.get("/api/test-orgs")
def test_orgs():

    result = (
        db._db()
        .table("organizations")
        .select("*")
        .execute()
    )

    return result.data


def _require_context(authorization: str):
    user = _require_user(authorization)

    ctx = auth.get_user_context(
        auth.user_id_from(user)
    )

    if not ctx:
        raise HTTPException(
            status_code=403,
            detail="User not assigned to any organization"
        )

    return user, ctx


  

 
@router.post("/api/admin/invite-org-admin")
async def invite_org_admin(
    request: Request,
    authorization: str = Header(None)
):

    user, ctx = _require_context(authorization)

    if ctx["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only SUPER_ADMIN can invite Org Admins"
        )

    body = await request.json()

    email = (body.get("email") or "").strip()
    organization_id = body.get("organization_id")

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email required"
        )

    result = (
        db._db()
        .table("organization_invites")
        .insert({
            "email": email,
            "organization_id": organization_id,
            "role": "ORG_ADMIN"
        })
        .execute()
    )

    return result.data[0]
@router.get("/api/test-invites")
def test_invites():

    result = (
        db._db()
        .table("organization_invites")
        .select("*")
        .execute()
    )

    return result.data
 
    
    
@router.get("/api/whoami")
def whoami(
    authorization: str = Header(None, alias="Authorization")
):

    user, ctx = _require_context(authorization)

    org_name = None
    if ctx["organization_id"]:
        org_res = db._db().table("organizations").select("name").eq("id", ctx["organization_id"]).execute()
        if org_res.data:
            org_name = org_res.data[0]["name"]

    return {
        "email": user["email"],
        "role": ctx["role"],
        "organization_id": ctx["organization_id"],
        "organization_name": org_name
    }

@router.get("/api/debug-header")
def debug_header(
    authorization: str = Header(None, alias="Authorization")
):
    return {
        "authorization": authorization
    }
    
    
@router.get("/api/test-google")
def test_google():

    return auth.get_user_context(
        "ef03406f-1c0f-459c-859d-ff8328a598c5"
    )    
    
def _require_user(authorization):
    try:
        return auth.verify_token(authorization)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))




@router.post("/api/admin/organizations")
async def create_organization(
    request: Request,
    authorization: str = Header(None)
):
    user, ctx = _require_context(authorization)

    if ctx["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only SUPER_ADMIN can create organizations"
        )

    body = await request.json()

    name = (body.get("name") or "").strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Organization name required"
        )

    result = (
        db._db()
        .table("organizations")
        .insert({
            "name": name,
            "status": "active"
        })
        .execute()
    )

    return result.data[0]



@router.post("/api/admin/create-organization")
async def create_organization(
    body: CreateOrganizationRequest
):

    organization_name = body.organization_name
    admin_email = body.admin_email

    org = (
        db._db()
        .table("organizations")
        .insert({
            "name": organization_name,
            "status": "active"
        })
        .execute()
    )

    org_id = org.data[0]["id"]

    (
        db._db()
        .table("organization_users")
        .insert({
            "organization_id": org_id,
            "role": "ORG_ADMIN",
            "email": admin_email,
            "status": "PENDING"
        })
        .execute()
    )

    return {
        "organization_id": org_id,
        "organization_name": organization_name,
        "admin_email": admin_email,
        "status": "created"
    }

@router.get("/api/admin/organizations")
def list_organizations(
    authorization: str = Header(None)
):
    ctx = auth.get_user_context(
    "da0c3caa-e907-4f1c-8747-e727f608dbd7"
)

    if ctx["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only SUPER_ADMIN can view organizations"
        )

    result = (
        db._db()
        .table("organizations")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return result.data




@router.get("/api/admin/organizations/{organization_id}")
def organization_details(
    organization_id: str
):

    org = (
        db._db()
        .table("organizations")
        .select("*")
        .eq("id", organization_id)
        .single()
        .execute()
    )

    users = (
        db._db()
        .table("organization_users")
        .select("*")
        .eq("organization_id", organization_id)
        .execute()
    )

    return {
        "organization": org.data,
        "users": users.data
    }
@router.get("/api/admin/users")
def list_all_users():

    result = (
        db._db()
        .table("organization_users")
        .select("*")
        .execute()
    )

    return result.data


@router.get("/api/org-admin/settings")
def get_org_settings(authorization: str = Header(None)):
    user, ctx = _require_context(authorization)
    org = db._db().table("organizations").select("email_template").eq("id", ctx["organization_id"]).execute()
    return {"email_template": org.data[0].get("email_template") if org.data else None}

@router.put("/api/org-admin/settings")
def update_org_settings(body: SettingsRequest, authorization: str = Header(None)):
    user, ctx = _require_context(authorization)
    if ctx["role"] != "ORG_ADMIN":
        raise HTTPException(status_code=403, detail="Only ORG_ADMIN can update settings")
    db._db().table("organizations").update({"email_template": body.email_template}).eq("id", ctx["organization_id"]).execute()
    return {"message": "Settings updated"}


@router.get("/api/org-admin/hrs")
def list_hrs(
    authorization: str = Header(None)
):

    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    result = (
        db._db()
        .table("organization_users")
        .select("*")
        .eq("organization_id", org_id)
        .eq("role", "HR")
        .execute()
    )

    return result.data

@router.delete("/api/org-admin/hr/{hr_id}")
def delete_hr(hr_id: str):

    result = (
        db._db()
        .table("organization_users")
        .delete()
        .eq("id", hr_id)
        .execute()
    )

    return {
        "message": "HR deleted"
    }
from datetime import datetime, timedelta, timezone

@router.post("/api/candidate/{candidate_id}/schedule")
def schedule_candidate(
    candidate_id: str,
    body: ScheduleCandidateRequest,
    authorization: str = Header(None)
):
    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    candidate_res = (
        db._db()
        .table("candidates")
        .select("*")
        .eq("id", candidate_id)
        .single()
        .execute()
    )

    if not candidate_res.data:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found"
        )

    candidate = candidate_res.data
    existing = (
    db._db()
    .table("scheduled_interviews")
    .select("*")
    .eq("candidate_id", candidate_id)
    .in_("status", ["scheduled", "launched"])
    .execute()
)

    if existing.data:
        raise HTTPException(
            status_code=400,
            detail="Interview already scheduled for this candidate"
        ) 

    job_res = (
        db._db()
        .table("job_openings")
        .select("*")
        .eq("id", candidate["job_opening_id"])
        .single()
        .execute()
    )

    if not job_res.data:
        raise HTTPException(
            status_code=404,
            detail="Job opening not found"
        )

    job = job_res.data

    keys = auth.get_user_keys_decrypted(
        auth.user_id_from(user)
    )

    analysis = extraction.analyze_documents(
        job["jd_text"],
        candidate["resume_text"],
        candidate["role"],
        keys=keys
    )

    questions = extraction.generate_question_plan(
        analysis,
        candidate["role"],
        body.question_count,
        keys=keys
    )

    session_id = db.create_session(
        bot_id=None,
        total_questions=len(questions),
        candidate_name=candidate["name"],
        candidate_email=candidate["email"],
        role=candidate["role"],
        status="scheduled",
        organization_id=org_id
    )

    scheduled_for = (
        datetime.now(timezone.utc)
        + timedelta(minutes=body.delay_minutes)
    )

    db.update_session_analysis(
        session_id,
        analysis,
        body.meeting_url,
        scheduled_for.isoformat(),
        job["jd_text"],
        candidate["resume_text"]
    )

    db.save_questions(
        session_id,
        questions
    )

    db.create_scheduled_interview(
        meeting_url=body.meeting_url,
        scheduled_for_iso=scheduled_for.isoformat(),
        candidate_email=candidate["email"],
        candidate_name=candidate["name"],
        role=candidate["role"],
        session_id=session_id,
        organization_id=org_id,
        candidate_id=candidate_id
    )

    when_human = scheduled_for.astimezone().strftime(
        "%Y-%m-%d %H:%M %Z"
    )

    org = db._db().table("organizations").select("name, email_template").eq("id", org_id).execute()
    custom_template = org.data[0].get("email_template") if org.data else None
    org_name = org.data[0].get("name") if org.data else None

    email_ok = scheduler.send_invite(
        candidate["email"],
        candidate["name"],
        body.meeting_url,
        role=candidate["role"],
        when=when_human,
        custom_template=custom_template,
        organization_name=org_name
    )

    return {
        "status": "scheduled",
        "session_id": session_id,
        "email_sent": email_ok,
        "questions_generated": len(questions)
    }
 
    
@router.delete("/api/admin/organizations/{organization_id}")
def delete_organization(
    organization_id: str
):

    db._db().table("organization_users")\
        .delete()\
        .eq("organization_id", organization_id)\
        .execute()

    db._db().table("organizations")\
        .delete()\
        .eq("id", organization_id)\
        .execute()

    return {
        "message": "Organization deleted"
    }
    
    
@router.get("/api/interviews")
def list_interviews(
    authorization: str = Header(None)
):
    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    result = (
        db._db()
        .table("scheduled_interviews")
        .select("*")
        .eq("organization_id", org_id)
        .order("created_at", desc=True)
        .execute()
    )

    return result.data






# ─── US-AG-01: upload + parse JD/resume ───────────────────
@router.post("/api/analyse")
async def analyse(resume: UploadFile = File(None), jd: UploadFile = File(None),
                  role: str = Form("Software Engineer"),
                  authorization: str = Header(None)):
    user = _require_user(authorization)
    keys = auth.get_user_keys_decrypted(auth.user_id_from(user))  # per-user LLM keys

    resume_text, jd_text, temp = "", "", {}
    if resume:
        rp = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{resume.filename}")
        with open(rp, "wb") as f:
            f.write(await resume.read())
        resume_text = extraction.extract_text(rp)
        temp["resume_path"] = rp
    if jd:
        jp = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{jd.filename}")
        with open(jp, "wb") as f:
            f.write(await jd.read())
        jd_text = extraction.extract_text(jp)
        temp["jd_path"] = jp
    if not resume_text and not jd_text:
        raise HTTPException(status_code=400, detail="Upload at least one document.")

    try:
        analysis = extraction.analyze_documents(jd_text, resume_text, role, keys=keys)
    except extraction.llm_stack.LLMExhausted as e:
        # signal the UI to prompt for a fresh key
        raise HTTPException(status_code=429,
                            detail={"error": "llm_exhausted", "providers": e.providers_tried})
    temp["resume_text"] = resume_text
    temp["jd_text"] = jd_text
    return {"analysis": analysis, "tempFiles": temp}



@router.post("/api/candidates/upload")
async def upload_candidate_resume(
    resume: UploadFile = File(...),
    job_opening_id: str = Form(...),
    authorization: str = Header(None)
):
    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    job = (
        db._db()
        .table("job_openings")
        .select("*")
        .eq("id", job_opening_id)
        .single()
        .execute()
    )

    if not job.data:
        raise HTTPException(
            status_code=404,
            detail="Job opening not found"
        )

    job = job.data

    rp = os.path.join(
        UPLOAD_DIR,
        f"{uuid.uuid4()}_{resume.filename}"
    )

    with open(rp, "wb") as f:
        f.write(await resume.read())

    resume_text = extraction.extract_text(rp)

    keys = auth.get_user_keys_decrypted(
        auth.user_id_from(user)
    )

    analysis = extraction.analyze_documents(
        job["jd_text"],
        resume_text,
        job["title"],
        keys=keys
    )

    candidate_name = analysis.get("candidateName") or "Unknown"
    candidate_email = analysis.get("candidateEmail") or ""

    db._db().table("candidates").insert({
        "name": candidate_name,
        "email": candidate_email,
        "role": job["title"],
        "resume_text": resume_text,
        "job_opening_id": job_opening_id,
        "organization_id": org_id,
        "analysis": analysis
    }).execute()

    return {
        "message": "Candidate created",
        "name": candidate_name,
        "email": candidate_email,
        "analysis": analysis
    }
# ─── US-AG-02 + scheduling: generate questions, store, email, schedule bot ──
@router.post("/api/schedule")
async def schedule(request: Request, authorization: str = Header(None)):
    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]
    uid = auth.user_id_from(user)
    keys = auth.get_user_keys_decrypted(uid)
    body = await request.json()

    analysis      = body.get("analysis", {})
    role          = body.get("role") or analysis.get("jobRole", "Software Engineer")
    qcount        = int(body.get("questionCount", 12))
    email         = (body.get("confirmedEmail") or analysis.get("candidateEmail") or "").strip()
    meeting_url   = (body.get("manualMeetingLink") or "").strip()
    temp          = body.get("tempFiles", {})
    delay_minutes = int(body.get("delayMinutes", 30))

    if not meeting_url:
        raise HTTPException(status_code=400, detail="A meeting link is required.")

    # 1. generate the dynamic question plan (US-AG-02)
    try:
        questions = extraction.generate_question_plan(analysis, role, qcount, keys=keys)
    except extraction.llm_stack.LLMExhausted as e:
        raise HTTPException(status_code=429,
                            detail={"error": "llm_exhausted", "providers": e.providers_tried})

    # 2. create candidate + session in OUR Supabase, store analysis + questions
    candidate_name  = analysis.get("candidateName", "Candidate")
    session_id = db.create_session(
    bot_id=None,
    total_questions=len(questions),
    candidate_name=candidate_name,
    candidate_email=email,
    role=role,
    status="scheduled",
    organization_id=org_id
)

    scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
    db.update_session_analysis(session_id, analysis, meeting_url, scheduled_for.isoformat(),
                               temp.get("jd_text"), temp.get("resume_text"))
    db.save_questions(session_id, questions)

    # 3. create the scheduled-interview row (the worker auto-deploys the bot at scheduled_for)
    sched = db.create_scheduled_interview(
    meeting_url=meeting_url,
    scheduled_for_iso=scheduled_for.isoformat(),
    candidate_email=email,
    candidate_name=candidate_name,
    role=role,
    session_id=session_id,
    organization_id=org_id
)

    # 4. email the invite now
    when_human = scheduled_for.astimezone().strftime("%Y-%m-%d %H:%M %Z")
    
    org_id = analysis.get("organization_id")
    custom_template = None
    org_name = None
    if org_id:
        org = db._db().table("organizations").select("name, email_template").eq("id", org_id).execute()
        custom_template = org.data[0].get("email_template") if org.data else None
        org_name = org.data[0].get("name") if org.data else None

    email_ok = scheduler.send_invite(email, candidate_name, meeting_url, role=role, when=when_human, custom_template=custom_template, organization_name=org_name) if email else False

    return {"status": "scheduled", "session_id": session_id,
            "scheduled_at": scheduled_for.isoformat().replace("+00:00", ""),
            "email_sent": email_ok, "questions_generated": len(questions)}


# ─── HR dashboard reads ───────────────────────────────────
@router.get("/api/hr/sessions")
def hr_sessions(
    authorization: str = Header(None)
):
    user, ctx = _require_context(authorization)

    org_id = ctx["organization_id"]

    return db.list_sessions_with_reports(org_id)

@router.get("/api/hr/session/{session_id}")
def hr_session(session_id: str, authorization: str = Header(None)):
    _require_user(authorization)
    return db.get_session_full(session_id)

@router.get("/api/hr/report/{session_id}")
def hr_report(session_id: str, authorization: str = Header(None)):
    _require_user(authorization)
    return db.get_report(session_id)

@router.get("/api/hr/session/{session_id}/recording")
def hr_recording_url(session_id: str, authorization: str = Header(None)):
    """Return a FRESH pre-signed recording URL (Recall's links expire in hours, so we re-fetch
    on demand using the session's bot_id instead of serving the stale cached URL)."""
    _require_user(authorization)
    bot_id = db.get_bot_id_for_session(session_id)
    if not bot_id:
        raise HTTPException(status_code=404, detail="No recording for this session")
    import app_full  # lazy import avoids a circular import at module load
    url = app_full.get_fresh_recording_url(bot_id)
    if not url:
        raise HTTPException(status_code=404, detail="Recording not available yet")
    return {"url": url}


@router.get("/api/hr/report/{session_id}/pdf")
def hr_report_pdf(session_id: str, authorization: str = Header(None)):
    _require_user(authorization)
    report = db.get_report(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report["session_id"] = session_id
    report["per_topic"] = report.get("per_topic", [])
    report["candidate"] = db.get_candidate_for_session(session_id)
    transcript = [{"speaker": a["speaker"], "text": a["text"],
                   "timestamp": a.get("created_at", "")} for a in db.read_answers(session_id)]
    path = report_pdf.build_report_pdf(report, transcript, out_dir="uploads/reports")
    return FileResponse(path, media_type="application/pdf", filename=os.path.basename(path))


# ─── API-key sidebar (per-user, encrypted, masked) ────────
@router.get("/api/keys")
def get_keys(authorization: str = Header(None)):
    user = _require_user(authorization)
    return auth.get_user_keys_masked(auth.user_id_from(user))

@router.post("/api/keys")
async def set_keys(request: Request, authorization: str = Header(None)):
    user = _require_user(authorization)
    body = await request.json()
    ok = auth.save_user_keys(auth.user_id_from(user),
                             {"gemini": body.get("gemini"), "claude": body.get("claude"),
                              "groq": body.get("groq")})
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save keys")
    return {"status": "saved", "keys": auth.get_user_keys_masked(auth.user_id_from(user))}

@router.get("/api/dashboard/hr")
def hr_dashboard(authorization: str = Header(None)):
    user, ctx = _require_context(authorization)
    org_id = ctx["organization_id"]
    
    candidates = db._db().table("candidates").select("*", count="exact").eq("organization_id", org_id).execute()
    interviews = db._db().table("scheduled_interviews").select("*", count="exact").eq("organization_id", org_id).execute()
    jobs = db._db().table("job_openings").select("*", count="exact").eq("organization_id", org_id).execute()
    
    return {
        "total_candidates": candidates.count,
        "total_interviews": interviews.count,
        "total_jobs": jobs.count
    }

@router.get("/api/job-openings/{job_id}/stats")
def job_stats(job_id: str, authorization: str = Header(None)):
    user, ctx = _require_context(authorization)
    
    cands = db._db().table("candidates").select("*", count="exact").eq("job_opening_id", job_id).execute()
    candidate_data = cands.data
    cand_ids = [c["id"] for c in candidate_data]
    
    if not cand_ids:
        return {
            "total_candidates": 0,
            "scheduled": 0,
            "completed": 0,
            "in_progress": 0
        }
        
    ints = db._db().table("scheduled_interviews").select("*").in_("candidate_id", cand_ids).execute()
    
    scheduled = len([i for i in ints.data if i.get("status") == "scheduled"])
    completed = len([i for i in ints.data if i.get("status") == "completed"])
    in_progress = len([i for i in ints.data if i.get("status") == "in_progress"])
    
    return {
        "total_candidates": cands.count,
        "scheduled": scheduled,
        "completed": completed,
        "in_progress": in_progress
    }