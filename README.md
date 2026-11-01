# CivicPulse AI
### Multimodal Civic Grievance Intelligence

An AI-assisted civic grievance reporting prototype that helps citizens document local infrastructure problems, understand photographic evidence, and prepare structured complaints for review.

> **Hackathon prototype:** CivicPulse creates and tracks records inside the CivicPulse application. It does not submit complaints to a government authority or provide an official government tracking number.

**Track:** Civic Pulse, Digital Governance & Public Information  
**Team:** Ak and Yadav

---

## Table of contents

- [Overview](#overview)
- [Key features](#key-features)
- [Technology stack](#technology-stack)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Installation on Windows](#installation-on-windows)
- [Configure Supabase](#configure-supabase)
- [Run the application](#run-the-application)
- [API endpoints](#api-endpoints)
- [Optional public demo tunnel](#optional-public-demo-tunnel)
- [Limitations, privacy and safety](#limitations-privacy-and-safety)
- [Future scope](#future-scope)
- [Acknowledgements](#acknowledgements)

## Overview

Citizens often encounter civic infrastructure issues such as potholes, damaged roads, water leakage and garbage accumulation. Preparing a clear complaint and identifying the appropriate department can be difficult.

CivicPulse AI lets a citizen upload a photograph, enter a location and optionally describe the issue. Google's Gemini multimodal AI analyzes the submitted image and generates a structured complaint draft for the citizen to review and edit before saving it in CivicPulse.

## Key features

- **Multimodal image analysis:** Uses Google Gemini to inspect an uploaded civic-issue photograph.
- **Issue classification:** Identifies the likely category of infrastructure problem.
- **Preliminary severity assessment:** Estimates visual severity and explains the evidence behind the estimate.
- **Visual explanation:** Describes relevant details visible in the submitted photograph.
- **Department recommendation:** Suggests a potentially responsible department; the exact authority must be verified for the location.
- **Complaint generation:** Creates an editable complaint title and message for citizen review.
- **Multilingual output:** Generates complaint drafts in the languages offered by the interface.
- **Persistent reports:** Saves citizen-approved report records to Supabase PostgreSQL when configured; SQLite is available for local development.
- **Dashboard:** Displays report records retrieved from the configured application database.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| Generative AI | Google Gemini multimodal API |
| Hosted database | Supabase PostgreSQL |
| Local database fallback | SQLite |
| Image processing | Python imaging libraries |
| Optional public demo tunnel | Cloudflare Quick Tunnel |

## How it works

```text
Citizen
  |
  v
Web application (HTML + CSS + JavaScript)
  |  image + location + description + selected language
  v
FastAPI backend
  |
  v
Google Gemini multimodal API
  |-- Image understanding
  |-- Issue classification
  |-- Preliminary severity assessment
  |-- Visual observations
  `-- Complaint draft generation
  |
  v
Citizen reviews and edits the draft
  |
  v
FastAPI report endpoint
  |
  +--> Supabase PostgreSQL (when configured)
  `--> SQLite (local fallback)
  |
  v
CivicPulse dashboard retrieves saved reports
```

## Project structure

```text
CivicPulse-AI/
├── app.py
├── requirements.txt
├── schema.sql
├── .env.example
├── .gitignore
├── README.md
├── backend/
│   ├── __init__.py
│   ├── ai_engine.py
│   └── database.py
├── static/
│   ├── app.js
│   └── style.css
└── templates/
    └── index.html
```

## Requirements

- Python 3.10 or newer
- A Google Gemini API key
- A Supabase project for hosted database persistence (optional for local-only development)
- Git, to clone the repository

## Installation on Windows

Run the following commands from the repository root—the folder containing `app.py`, `requirements.txt` and `.env.example`.

### 1. Clone the repository

```powershell
git clone https://github.com/EqualPlayer/CivicPulse-AI.git
cd CivicPulse-AI
```

### 2. Create and activate a virtual environment

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for this terminal session, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create the environment file

Copy the example file to create your private local configuration:

```powershell
Copy-Item .env.example .env
```

Open `.env` in VS Code or Notepad and enter your own credentials. Do not commit `.env` to GitHub.

## Configure Supabase

1. Create a Supabase project.
2. Open the Supabase SQL Editor.
3. Run the SQL in `schema.sql` to create the `public.civic_reports` table and enable Row Level Security.
4. Copy the project's URL from the Supabase dashboard.
5. Create or copy a Supabase **Secret key** for server-side use.
6. Add the URL and secret key to `.env` as shown below.

The Supabase Secret key has elevated access. Keep it only on the Python backend. Never expose it in browser JavaScript, HTML, screenshots or a public repository.

## Environment variables

Use `.env.example` as the template. The local `.env` should contain your own values:

```dotenv
# AI provider
AI_PROVIDER=gemini

# Google Gemini API
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=YOUR_SUPPORTED_GEMINI_MODEL

# Supabase hosted database
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_SECRET_KEY=YOUR_SUPABASE_SECRET_KEY

# Local SQLite fallback and upload limit
DATABASE_PATH=civicpulse.db
MAX_UPLOAD_MB=8
```

Obtain credentials here:

- Gemini API key: https://aistudio.google.com/api-keys
- Supabase Project URL and Secret key: Supabase Dashboard → Project Settings / Connect → API settings

If Supabase credentials are not configured, the application can use local SQLite for development. For a public demonstration, configure Supabase so report records persist in the hosted database.

## Run the application

From the repository root, with the virtual environment activated:

```powershell
python -m uvicorn app:app --reload
```

Open the application in a browser:

```text
http://127.0.0.1:8000
```

Check backend and database status:

```text
http://127.0.0.1:8000/api/health
```

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Reports backend, AI provider and database health |
| `/api/analyze` | POST | Accepts an image and form fields for multimodal civic-issue analysis |
| `/api/reports` | POST | Saves a citizen-approved report |
| `/api/reports` | GET | Retrieves saved report records for the dashboard |

## Optional public demo tunnel

For a temporary demonstration from another device, Cloudflare Quick Tunnel can expose the local FastAPI server. First start the application, then open a second terminal and run:

```powershell
cloudflared tunnel --protocol http2 --url http://localhost:8000
```

Cloudflare prints a temporary HTTPS URL ending in `trycloudflare.com`. Keep both the FastAPI server and tunnel running while the demo is active. The URL can change when a new tunnel is created. A Quick Tunnel is for demonstration, not permanent production hosting.

## Limitations, privacy and safety

- AI severity estimates are preliminary visual assessments, not emergency assessments or professional engineering inspections.
- Department suggestions are general guidance. The responsible authority must be verified for the user's exact jurisdiction.
- Saving a report creates a CivicPulse application record. It does **not** file a complaint with a government authority and does not create an official government tracking number.
- AI-generated content should be reviewed and edited by the citizen before saving.
- Unrelated, unclear or low-quality images may result in unreliable analysis. Use a genuine, relevant photograph of the reported issue.
- Images are sent to the configured AI provider for analysis. This initial version does not retain uploaded images as permanent evidence.
- Keep all API credentials in `.env`. The `.env` file is excluded from version control; `.env.example` contains placeholders only.

## Future scope

- Citizen registration and secure authentication.
- Personal complaint history and status tracking.
- Authorized administrative review and status updates.
- Verified government-jurisdiction lookup using official datasets.
- Integration with official grievance portals where permitted.
- Secure cloud storage for photographic evidence.
- Voice-based civic reporting and expanded regional-language support.

## Acknowledgements

Built by **Ak and Yadav** as a hackathon prototype exploring how multimodal Generative AI can make civic reporting more accessible.

Thank you for checking out CivicPulse AI!
