import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DATABASE_PATH", "civicpulse.db")
TABLE_NAME = "civic_reports"


def _supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()

    key = (
        os.getenv("SUPABASE_SECRET_KEY", "").strip()
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )

    if not url or not key:
        return None

    from supabase import create_client

    return create_client(url, key)


def supabase_connection_status() -> str:
    client = _supabase_client()

    if client is None:
        return "sqlite-local"

    try:
        client.table(TABLE_NAME).select("id").limit(1).execute()
        return "supabase"

    except Exception as exc:
        print(
            f"Supabase connection failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return "supabase-error"

def supabase_connection_status() -> str:
    client = _supabase_client()

    if client is None:
        return "sqlite-local"

    try:
        client.table(TABLE_NAME).select("id").limit(1).execute()
        return "supabase"

    except Exception as exc:
        print(
            f"Supabase connection failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return "supabase-error"


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS civic_reports (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                image_observation TEXT NOT NULL,
                location TEXT NOT NULL,
                user_description TEXT,
                recommended_department TEXT NOT NULL,
                complaint_title TEXT NOT NULL,
                complaint_body TEXT NOT NULL,
                language TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                provider TEXT NOT NULL
            )"""
        )


def create_report(analysis: dict[str, Any], location: str, user_description: str) -> dict[str, Any]:
    report = {
        "id": f"CP-{uuid.uuid4().hex[:10].upper()}",
        "category": analysis["category"],
        "severity": analysis["severity"],
        "confidence": float(analysis["confidence"]),
        "image_observation": analysis["image_observation"],
        "location": location.strip(),
        "user_description": user_description.strip(),
        "recommended_department": analysis["recommended_department"],
        "complaint_title": analysis["complaint_title"],
        "complaint_body": analysis["complaint_body"],
        "language": analysis["language"],
        "status": "Submitted to CivicPulse (not yet filed with government)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": analysis.get("provider", "unknown"),
    }

    client = _supabase_client()
    if client:
        response = client.table(TABLE_NAME).insert(report).execute()
        rows = getattr(response, "data", None) or []
        if not rows:
            raise RuntimeError("Supabase did not confirm the report insert.")
        return rows[0]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO civic_reports
            (id, category, severity, confidence, image_observation, location, user_description,
             recommended_department, complaint_title, complaint_body, language, status, created_at, provider)
            VALUES (:id, :category, :severity, :confidence, :image_observation, :location, :user_description,
                    :recommended_department, :complaint_title, :complaint_body, :language, :status, :created_at, :provider)""",
            report,
        )
    return report


def list_reports(limit: int = 50) -> list[dict[str, Any]]:
    client = _supabase_client()
    if client:
        response = client.table(TABLE_NAME).select("*").order("created_at", desc=True).limit(limit).execute()
        return getattr(response, "data", None) or []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM civic_reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]
