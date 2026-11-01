import os
from pathlib import Path
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


@app.post("/api/reports")
def submit_report(payload: dict):
    analysis = payload.get("analysis")
    if not isinstance(analysis, dict):
        raise HTTPException(status_code=400, detail="Missing AI analysis. Analyze the image first.")
    location = str(payload.get("location", "")).strip()
    if len(location) < 3:
        raise HTTPException(status_code=400, detail="Please provide a more specific location.")
    try:
        report = create_report(analysis, location, str(payload.get("description", "")))
        return {"report": report}
    except Exception as exc:
        print(f"Database insert failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail="Could not save the report. Check database configuration and retry.") from exc


@app.get("/api/reports")
def reports():
    try:
        rows = list_reports()
        return {
            "reports": rows,
            "total": len(rows),
            "high_priority": sum(1 for row in rows if row.get("severity") in {"High", "Critical"}),
        }
    except Exception as exc:
        print(f"Database read failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=502, detail="Could not load reports from the database.") from exc
