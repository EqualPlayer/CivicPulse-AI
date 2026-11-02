import os
import json
import uuid
from datetime import datetime, timezone
import logging
logger = logging.getLogger(__name__)

from fastapi.responses import FileResponse
from fastapi import Depends
from pydantic import BaseModel

from backend.auth import get_admin_client, require_roles
from pathlib import Path
from backend.auth import get_current_user, require_roles
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from backend.ai_engine import analyze_civic_image
from backend.database import (
    create_report,
    init_db,
    list_reports,
    supabase_connection_status,
)

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "8"))
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(title="CivicPulse AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={"request": request}
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "provider": "gemini",
        "ai_key_configured": bool(
            os.getenv("GEMINI_API_KEY")
        ),
        "database": supabase_connection_status()
    }

@app.get("/api/auth/me")
def auth_me(
    current_user: dict = Depends(get_current_user)
):
    return {
        "authenticated": True,
        "user": current_user
    }


@app.get("/api/staff/auth-check")
def staff_auth_check(
    current_user: dict = Depends(
        require_roles("worker", "admin")
    )
):
    return {
        "authorized": True,
        "user": current_user
    }

@app.get("/api/config")
def public_config():
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    publishable_key = os.getenv(
        "SUPABASE_PUBLISHABLE_KEY", ""
    ).strip()

    if not supabase_url or not publishable_key:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured."
        )

    return {
        "supabase_url": supabase_url,
        "supabase_publishable_key": publishable_key
    }


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    location: str = Form(""),
    description: str = Form(""),
    language: str = Form("English"),
):
    if image.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, or WEBP image.")
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(image_bytes) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Image must be smaller than {MAX_UPLOAD_MB} MB.")

    try:
        analysis = await run_in_threadpool(
        analyze_civic_image,
        image_bytes=image_bytes,
        mime_type=image.content_type,
        description=description,
        location=location,
        language=language,
        )
        return {"analysis": analysis}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Keep API/provider details out of the browser; log the real cause in server terminal.
        print(f"AI analysis failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {exc}") from exc



class ReportStatusUpdate(BaseModel):
    status: str
    remark: str


ALLOWED_STATUSES = {
    "pending",
    "under_review",
    "in_progress",
    "resolved",
    "rejected",
}


def signed_evidence_url(client, report):
    path = report.get("evidence_path")
    if not path:
        report["evidence_url"] = None
        return report

    try:
        result = client.storage.from_("civic-evidence").create_signed_url(
            path, 300
        )
        report["evidence_url"] = (
            result.get("signedURL")
            or result.get("signedUrl")
        )
    except Exception:
        report["evidence_url"] = None

    return report


@app.post("/api/reports")
async def submit_report(
    analysis: str = Form(...),
    location: str = Form(...),
    description: str = Form(""),
    image: UploadFile = File(...),
    current_user: dict = Depends(require_roles("citizen", "worker", "admin")),
):
    if image.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(415, "Upload a JPG, PNG or WEBP image.")

    image_bytes = await image.read()

    if not image_bytes or len(image_bytes) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, "Image is empty or exceeds the upload limit.")

    if len(location.strip()) < 3:
        raise HTTPException(400, "Please provide a valid location.")

    try:
        analysis_data = json.loads(analysis)
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid AI analysis data.")

    required = [
        "category", "severity", "confidence", "image_observation",
        "recommended_department", "complaint_title", "complaint_body",
        "language",
    ]

    if not isinstance(analysis_data, dict) or any(
        key not in analysis_data for key in required
    ):
        raise HTTPException(400, "AI analysis is incomplete.")

    client = get_admin_client()

    report_id = f"CP-{uuid.uuid4().hex[:10].upper()}"
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[image.content_type]

    evidence_path = (
        f"{current_user['id']}/{report_id}.{extension}"
    )

    now = datetime.now(timezone.utc).isoformat()

    try:
        # Store the original photograph privately.
        client.storage.from_("civic-evidence").upload(
            evidence_path,
            image_bytes,
            file_options={
                "content-type": image.content_type,
                "upsert": "false",
            },
        )

        report = {
            "id": report_id,
            "user_id": current_user["id"],
            "assigned_to": None,
            "evidence_path": evidence_path,
            "category": analysis_data["category"],
            "severity": analysis_data["severity"],
            "confidence": float(analysis_data["confidence"]),
            "image_observation": analysis_data["image_observation"],
            "location": location.strip(),
            "user_description": description.strip(),
            "recommended_department": analysis_data["recommended_department"],
            "complaint_title": str(analysis_data["complaint_title"]).strip(),
            "complaint_body": str(analysis_data["complaint_body"]).strip(),
            "language": analysis_data["language"],
            "status": "pending",
            "current_remark": "Complaint received and awaiting review.",
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "rejected_at": None,
            "legacy_unassigned": False,
            "provider": "gemini",
        }

        saved = (
            client.table("civic_reports")
            .insert(report)
            .execute()
        )

        if not saved.data:
            raise RuntimeError("Database did not confirm the report.")

        try:
            client.table("report_status_history").insert({
                "report_id": report_id,
                "changed_by": current_user["id"],
                "old_status": None,
                "new_status": "pending",
                "remark": "Complaint submitted by citizen.",
            }).execute()
        except Exception:
            logger.exception("Could not create initial status history.")

        return {"report": saved.data[0]}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Complaint submission failed.")
        raise HTTPException(
            502,
            "Could not save the complaint. Please try again."
        ) from exc


@app.get("/api/my-reports")
def my_reports(
    current_user: dict = Depends(require_roles("citizen")),
):
    client = get_admin_client()

    result = (
        client.table("civic_reports")
        .select("*")
        .eq("user_id", current_user["id"])
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    reports = [
        signed_evidence_url(client, row)
        for row in (result.data or [])
    ]

    return {"reports": reports, "total": len(reports)}


@app.get("/api/staff/reports")
def staff_reports(
    current_user: dict = Depends(require_roles("worker", "admin")),
):
    client = get_admin_client()

    query = client.table("civic_reports").select("*")

    if current_user["role"] == "worker":
        query = query.eq("assigned_to", current_user["id"])

    result = (
        query.order("created_at", desc=True)
        .limit(200)
        .execute()
    )

    reports = [
        signed_evidence_url(client, row)
        for row in (result.data or [])
    ]

    return {"reports": reports, "total": len(reports)}


@app.patch("/api/staff/reports/{report_id}/status")
def update_report_status(
    report_id: str,
    update: ReportStatusUpdate,
    current_user: dict = Depends(require_roles("worker", "admin")),
):
    new_status = update.status.strip().lower()
    remark = update.remark.strip()

    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(400, "Invalid complaint status.")

    if len(remark) < 5:
        raise HTTPException(400, "Please provide an official remark.")

    client = get_admin_client()

    result = (
        client.table("civic_reports")
        .select("id,status,assigned_to")
        .eq("id", report_id)
        .limit(1)
        .execute()
    )

    rows = result.data or []

    if not rows:
        raise HTTPException(404, "Complaint not found.")

    old_report = rows[0]

    if (
        current_user["role"] == "worker"
        and old_report.get("assigned_to") != current_user["id"]
    ):
        raise HTTPException(
            403,
            "You can only update complaints assigned to you."
        )

    now = datetime.now(timezone.utc).isoformat()

    changes = {
        "status": new_status,
        "current_remark": remark,
        "updated_at": now,
        "resolved_at": now if new_status == "resolved" else None,
        "rejected_at": now if new_status == "rejected" else None,
    }

    client.table("civic_reports").update(changes).eq(
        "id", report_id
    ).execute()

    client.table("report_status_history").insert({
        "report_id": report_id,
        "changed_by": current_user["id"],
        "old_status": old_report["status"],
        "new_status": new_status,
        "remark": remark,
    }).execute()

    return {
        "success": True,
        "report_id": report_id,
        "status": new_status,
        "remark": remark,
    }


@app.get("/api/public/statistics")
def public_statistics():
    client = get_admin_client()

    result = (
        client.table("civic_reports")
        .select("id,severity,status")
        .execute()
    )

    rows = result.data or []

    counts = {
        status: sum(1 for row in rows if row["status"] == status)
        for status in ALLOWED_STATUSES
    }

    return {
        "total": len(rows),
        "high_priority": sum(
            1 for row in rows
            if row["severity"] in {"High", "Critical"}
        ),
        "status_counts": counts,
        "database": "supabase",
    }



class WorkerAssignment(BaseModel):
    worker_id: str


class UserRoleUpdate(BaseModel):
    role: str


@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(
        Path(__file__).resolve().parent / "templates" / "admin.html"
    )


@app.get("/api/admin/users")
def admin_list_users(
    current_user: dict = Depends(require_roles("admin")),
):
    client = get_admin_client()

    roles = (
        client.table("user_roles")
        .select("user_id,role,is_active")
        .order("created_at", desc=True)
        .execute()
    )

    profiles = (
        client.table("profiles")
        .select("id,display_name")
        .execute()
    )

    profile_map = {
        p["id"]: p for p in (profiles.data or [])
    }

    users = []

    for item in roles.data or []:
        profile = profile_map.get(item["user_id"], {})
        users.append({
            "id": item["user_id"],
            "display_name": profile.get("display_name") or "CivicPulse user",
            "role": item["role"],
            "is_active": item["is_active"],
        })

    return {"users": users}


@app.patch("/api/admin/users/{user_id}/role")
def admin_update_role(
    user_id: str,
    update: UserRoleUpdate,
    current_user: dict = Depends(require_roles("admin")),
):
    if update.role not in ("citizen", "worker"):
        raise HTTPException(
            400,
            "Only citizen or worker roles can be assigned here."
        )

    client = get_admin_client()

    result = (
        client.table("user_roles")
        .update({
            "role": update.role,
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(404, "User not found.")

    return {"success": True, "role": update.role}


@app.patch("/api/admin/reports/{report_id}/assign")
def admin_assign_worker(
    report_id: str,
    assignment: WorkerAssignment,
    current_user: dict = Depends(require_roles("admin")),
):
    client = get_admin_client()

    worker = (
        client.table("user_roles")
        .select("user_id,role,is_active")
        .eq("user_id", assignment.worker_id)
        .limit(1)
        .execute()
    )

    if not worker.data:
        raise HTTPException(404, "Worker account not found.")

    worker_record = worker.data[0]

    if worker_record["role"] != "worker" or not worker_record["is_active"]:
        raise HTTPException(400, "Select an active worker account.")

    result = (
        client.table("civic_reports")
        .update({
            "assigned_to": assignment.worker_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", report_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(404, "Complaint not found.")

    return {"success": True, "assigned_to": assignment.worker_id}

@app.get("/worker", include_in_schema=False)
def worker_page():
    return FileResponse(
        Path(__file__).resolve().parent / "templates" / "worker.html"
    )

@app.get("/api/staff/reports/{report_id}/history")
def worker_report_history(
    report_id: str,
    current_user: dict = Depends(require_roles("worker", "admin")),
):
    client = get_admin_client()

    report = (
        client.table("civic_reports")
        .select("id,assigned_to")
        .eq("id", report_id)
        .limit(1)
        .execute()
    )

    if not report.data:
        raise HTTPException(404, "Complaint not found.")

    if (
        current_user["role"] == "worker"
        and report.data[0]["assigned_to"] != current_user["id"]
    ):
        raise HTTPException(403, "This complaint is not assigned to you.")

    history = (
        client.table("report_status_history")
        .select("*")
        .eq("report_id", report_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {"history": history.data or []}

@app.get("/worker", include_in_schema=False)
def worker_page():
    worker_file = Path(__file__).resolve().parent / "templates" / "worker.html"

    if not worker_file.exists():
        raise HTTPException(404, "worker.html not found")

    return FileResponse(worker_file)

@app.get("/api/my-reports/{report_id}/history")
def my_report_history(
    report_id: str,
    current_user: dict = Depends(
        require_roles("citizen", "worker", "admin")
    ),
):
    client = get_admin_client()

    report = (
        client.table("civic_reports")
        .select("id,user_id")
        .eq("id", report_id)
        .limit(1)
        .execute()
    )

    if not report.data:
        raise HTTPException(404, "Complaint not found.")

    if report.data[0]["user_id"] != current_user["id"]:
        raise HTTPException(404, "Complaint not found.")

    result = (
        client.table("report_status_history")
        .select("old_status,new_status,remark,created_at")
        .eq("report_id", report_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {"history": result.data or []}