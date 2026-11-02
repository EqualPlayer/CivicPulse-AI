# CivicPulse AI

### Multimodal Civic Grievance Intelligence

CivicPulse AI is a multimodal civic grievance reporting and workflow prototype. Citizens can submit photographs of local infrastructure problems, receive an AI-generated issue assessment and complaint draft, and track the report inside CivicPulse. Authorized workers can review assigned reports and update their status, while administrators can manage users, assign reports, and monitor the overall queue.

> **Hackathon prototype:** CivicPulse creates and tracks records inside the CivicPulse application. It does **not** submit complaints to a government authority, guarantee action by a public body, or provide an official government grievance number.

**Track:** Civic Pulse, Digital Governance & Public Information  
**Team:** Ak and Yadav

---

## Table of contents

- [What CivicPulse does](#what-civicpulse-does)
- [Features](#features)
- [User roles and workflow](#user-roles-and-workflow)
- [How the system works](#how-the-system-works)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Local installation](#local-installation)
- [Environment variables and API keys](#environment-variables-and-api-keys)
- [Supabase database and storage setup](#supabase-database-and-storage-setup)
- [Authentication setup](#authentication-setup)
- [Roles and first administrator setup](#roles-and-first-administrator-setup)
- [Run CivicPulse](#run-civicpulse)
- [Application pages](#application-pages)
- [API reference](#api-reference)
- [Security design](#security-design)
- [Privacy, limitations and responsible use](#privacy-limitations-and-responsible-use)
- [Demo on another device](#demo-on-another-device)
- [Ideas for pilots and future development](#ideas-for-pilots-and-future-development)
- [Troubleshooting](#troubleshooting)
- [Acknowledgements](#acknowledgements)

---

## What CivicPulse does

Civic issues such as potholes, damaged roads, overflowing waste, broken streetlights, and water leakage are often reported with incomplete descriptions or sent to the wrong department. CivicPulse helps turn a citizen's photograph and description into a structured report that can be reviewed and acted on within the application.

A citizen uploads a relevant photograph, enters the location, and optionally adds a description. Google's Gemini multimodal model analyzes the image and returns structured information such as the likely issue category, preliminary visual severity, observations, suggested department, and an editable complaint draft. The citizen reviews the draft before submitting it.

After submission, the report is stored in the configured Supabase project. Its workflow can then be followed by the citizen, an assigned worker, and an administrator.

## Features

### AI-assisted citizen reporting

- **Multimodal image analysis:** Uses Google Gemini to inspect a submitted civic-issue photograph.
- **Issue classification:** Suggests the likely type of civic or infrastructure problem.
- **Preliminary severity assessment:** Estimates visual severity and provides observations that support the estimate.
- **Visual explanation:** Describes relevant details visible in the photograph.
- **Department recommendation:** Suggests a potentially responsible department. The correct authority still needs to be verified for the relevant jurisdiction.
- **Editable complaint generation:** Creates a complaint title and description that the citizen can review and edit before submission.
- **Language selection:** Generates the complaint draft in the languages offered by the interface.
- **Evidence attachment:** Stores submitted report photographs in a private Supabase Storage bucket.

### Citizen portal

- Email/password registration and sign-in through Supabase Auth.
- Google sign-in when the Google provider is configured.
- Personal report history; citizens see only reports associated with their account.
- Report status and the latest worker/admin remark.
- Report status history, so the citizen can follow changes over time.
- Signed links for viewing private evidence images.

### Worker portal

- Protected worker sign-in and role verification.
- A queue containing reports assigned to the signed-in worker.
- Access to report details and attached evidence for assigned reports.
- Status updates with a required explanatory remark.
- Status history for the reports the worker is authorized to access.

### Administrator portal

- Protected administrator access to the report queue and dashboard statistics.
- View report records and evidence across the application.
- View registered users and their current roles.
- Promote an eligible citizen account to the worker role through the protected role-management workflow.
- Assign reports to active workers.
- Review report status and workflow information.

### Report workflow

Reports use the following status values:

`pending` → `under_review` → `in_progress` → `resolved`

A report may also be marked `rejected` when it cannot be accepted for processing. Status changes are accompanied by remarks and recorded in the report status history.

## User roles and workflow

| Role | Main permissions |
|---|---|
| **Citizen** | Create reports, view their own reports, read remarks and status history. |
| **Worker** | View reports assigned to them, inspect evidence, and update the status of assigned reports with a remark. |
| **Admin** | View the overall queue, manage citizen/worker roles, assign reports to active workers, and monitor report activity. |

Newly registered accounts receive the `citizen` role automatically. A user cannot make themselves a worker or administrator through the public registration form. An existing administrator must promote a user to worker; initial administrator provisioning is performed by the project owner in the database.

## How the system works

```text
Citizen browser
    |
    | Photograph + location + description + selected language
    v
FastAPI application
    |
    v
Google Gemini multimodal API
    |-- Image understanding
    |-- Issue classification
    |-- Preliminary severity assessment
    |-- Visual observations
    `-- Editable complaint draft
    |
    v
Citizen reviews and edits the draft
    |
    v
Authenticated report submission
    |
    +--> Supabase Storage (private evidence bucket)
    `--> Supabase PostgreSQL (report and workflow records)
             |
             +--> Citizen: own reports and history
             +--> Worker: assigned reports and status updates
             `--> Admin: queue, user roles and assignments
```

The browser uses Supabase Auth to sign in and obtains an access token. Protected API requests send that token to FastAPI. The backend verifies the token, reads the user's active application role, and applies the relevant ownership, assignment, and role checks before returning or changing data.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend/API | Python, FastAPI |
| Authentication | Supabase Auth, Supabase JavaScript client |
| Generative AI | Google Gemini multimodal API |
| Database | Supabase PostgreSQL |
| Evidence storage | Private Supabase Storage bucket with signed URLs |
| Image handling | Python imaging libraries and upload validation |
| Optional demo tunnel | Cloudflare Quick Tunnel |

## Project structure

The main application files are organized as follows. File names can differ slightly between branches as the project evolves.

```text
CivicPulse-AI/
├── app.py
├── requirements.txt
├── schema.sql
├── schema_upgrade_citizen_admin.sql
├── .env.example
├── .gitignore
├── README.md
├── backend/
│   ├── __init__.py
│   ├── ai_engine.py
│   ├── auth.py
│   └── database.py
├── static/
│   ├── app.js
│   ├── admin.js
│   ├── worker.js
│   └── style.css
└── templates/
    ├── index.html
    ├── admin.html
    └── worker.html
```

## Requirements

- Python 3.10 or newer.
- Git.
- A Google AI Studio API key for Gemini analysis.
- A Supabase project for authentication, PostgreSQL, and private evidence storage.
- A Google Cloud OAuth web client only when Google sign-in is required.

**Supabase is required for the complete citizen/worker/admin workflow.** A local SQLite fallback, where available in the checked-out version, is intended only for limited local development; it does not replace Supabase Auth, role management, or private evidence storage.

## Local installation

The following commands are for Windows PowerShell. Run them from the repository root—the directory containing `app.py` and `requirements.txt`.

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

If PowerShell blocks activation in the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create your local environment file

```powershell
Copy-Item .env.example .env
```

Open `.env` in VS Code or a text editor and add your own credentials as described below. **Never commit `.env` to GitHub.**

## Environment variables and API keys

Use the following as a guide for the local `.env` file. Keep the real values private and do not put them in frontend JavaScript, HTML, screenshots, issue reports, or Git commits.

```dotenv
# Google Gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.5-flash-lite

# Supabase project
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY=YOUR_SUPABASE_SECRET_KEY

# Optional local-development settings, if used by your checkout
DATABASE_PATH=civicpulse.db
MAX_UPLOAD_MB=8
```

### Where to get each key

| Variable | Where to get it | How it is used |
|---|---|---|
| `GEMINI_API_KEY` | [Google AI Studio – API keys](https://aistudio.google.com/api-keys) | Server-side Gemini image analysis. |
| `GEMINI_MODEL` | A model enabled for your Gemini API project | Selects the Gemini model. The value above is the model used during project testing; change it only to a model supported by your API account and current code. |
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API | Identifies your Supabase project. |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase Dashboard → Project Settings → API Keys | Used by the browser's Supabase Auth client and the public configuration endpoint. It is designed to be exposed in a browser, but access must still be protected by backend authorization and database policy configuration. |
| `SUPABASE_SECRET_KEY` | Supabase Dashboard → Project Settings → API Keys | Used only by the FastAPI server for privileged database and storage operations. Treat it like a password. |

Supabase may label the public key as a **publishable key** and the privileged key as a **secret key**. Use the matching key types from your project's dashboard. Do not place the secret key in a variable exposed to the frontend.

If a key has ever been committed to a public repository or shared in a screenshot, revoke/rotate it in the provider dashboard and update your local `.env` file. Removing it from the latest commit does not make an exposed key safe again.

## Supabase database and storage setup

### 1. Create a Supabase project

Create a project at [Supabase](https://supabase.com/). Select a strong database password and keep it private.

### 2. Run the SQL files in order

Open **Supabase Dashboard → SQL Editor** and run the repository SQL scripts:

1. Run `schema.sql` to create the original civic report database structure and its baseline policies.
2. Run `schema_upgrade_citizen_admin.sql` to add user profiles, application roles, report ownership and assignment fields, status history, the new status workflow, and the storage bucket configuration.

If the base schema has already been installed in your project, do not recreate it unnecessarily; run the upgrade script once. Review the SQL before executing it on any database containing data. Keep a database backup before applying schema changes to an existing deployment.

The upgrade script is designed to configure the `civic-evidence` Storage bucket as **private**, with an 8 MB upload limit and image MIME-type restrictions. Report evidence is uploaded by the backend and returned to authorized users through short-lived signed URLs.

### 3. Add Supabase values to `.env`

Copy the project URL, publishable key, and secret key from the Supabase dashboard into the matching variables. Restart FastAPI after changing `.env` so the backend reads the new values.

### 4. Keep the database server-side

The application uses the FastAPI backend for report, role, and storage operations. Do not add the Supabase secret key to the browser client. Do not loosen table permissions simply to make browser-side queries work; use the authenticated API routes.

## Authentication setup

CivicPulse uses Supabase Auth for identity management. Email/password authentication is the primary sign-in method. Google sign-in is optional and requires provider configuration.

### Email/password authentication

1. Open **Supabase Dashboard → Authentication → Sign In / Providers** (the dashboard wording may vary slightly).
2. Enable the **Email** provider.
3. Keep new user sign-up enabled if you want users to register themselves.
4. Configure email confirmation according to your demo or deployment needs. When confirmation is enabled, users must confirm their email before they can sign in.
5. For a real deployment, configure a trusted SMTP email provider under Supabase Auth settings. Default test email delivery is not intended for a production service.

### Configure the application redirect URLs

In **Supabase Dashboard → Authentication → URL Configuration**:

- Set the local development Site URL to `http://127.0.0.1:8000`.
- Add `http://127.0.0.1:8000/**` to the allowed redirect URLs.
- Add `http://localhost:8000/**` if you also use `localhost`.
- When hosting the app elsewhere, add the exact HTTPS application URL and the required callback path(s) for that deployment.

The redirect URL must match the address from which you open the app. `localhost` and `127.0.0.1` are different origins, so configure the one you actually use.

### Google sign-in (optional)

Google sign-in uses a Google OAuth web application and Supabase as the OAuth callback handler.

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Configure the OAuth consent screen with the app details required by Google.
3. Create an OAuth Client ID with application type **Web application**.
4. In the Google OAuth client, add these local authorized JavaScript origins:
   - `http://127.0.0.1:8000`
   - `http://localhost:8000` (only if you use it)
5. In the Google OAuth client, add the Supabase callback URL as an **Authorized redirect URI**:
   - `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
6. Copy the Google Client ID and Client Secret into **Supabase Dashboard → Authentication → Sign In / Providers → Google**, and enable the Google provider.
7. Save the configuration and test Google sign-in from the local CivicPulse page.

**Important:** The Google authorized redirect URI is the Supabase callback URL, not your local FastAPI URL. The local application URL belongs in Google authorized JavaScript origins and in Supabase's allowed redirect URL list.

For a temporary Cloudflare URL, add that exact HTTPS origin to the Google OAuth client's authorized JavaScript origins and add the app redirect URL to Supabase's allowed redirect URLs. Quick Tunnel URLs change, so this may need to be repeated when a new URL is generated. For a stable public deployment, use a permanent domain and HTTPS.

Phone/SMS authentication is not part of the current setup. Enabling it requires an SMS provider and appropriate provider credentials.

## Roles and first administrator setup

### Automatic citizen role

The database trigger created by the upgrade script creates a profile and a `citizen` role when a new Supabase Auth user registers. Public registration does not provide a role selector. Users cannot assign themselves worker or admin privileges.

### Create the first administrator

The first administrator must be provisioned manually by the project owner after registering the intended admin account:

1. Register and confirm the account through the CivicPulse sign-in page.
2. In Supabase, open **SQL Editor**.
3. Replace the email below with the email address of that account and run the statement:

```sql
UPDATE public.user_roles
SET role = 'admin',
    is_active = TRUE,
    updated_at = NOW()
WHERE user_id = (
    SELECT id
    FROM auth.users
    WHERE email = 'admin@example.com'
);
```

4. Sign out and sign back in, then open `/admin`.
5. Confirm that the account can access the administrator dashboard.

Run this only for an account you control. If the query updates zero rows, check that the user has registered and that the email matches the Supabase Auth account.

### Add a worker

1. Have the intended worker register through the normal sign-up flow.
2. Sign in with an administrator account and open `/admin`.
3. Find the new user in user management and promote the account to `worker`.
4. Assign one or more reports to that active worker.
5. The worker can then sign in and open `/worker` to see assigned reports.

The admin role-management API is intentionally limited to assigning `citizen` and `worker`; it does not let an administrator create another admin through the normal UI. Initial admin provisioning remains an owner-controlled database operation.

## Run CivicPulse

From the project root, with `.venv` activated and `.env` configured:

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open the application:

- Citizen application: `http://127.0.0.1:8000/`
- Worker portal: `http://127.0.0.1:8000/worker`
- Administrator portal: `http://127.0.0.1:8000/admin`
- Health check: `http://127.0.0.1:8000/api/health`
- Public app configuration: `http://127.0.0.1:8000/api/config`
- Interactive API docs (development): `http://127.0.0.1:8000/docs`

For development, `--reload` restarts the app when Python files change. Do not use the development reload server as a production deployment configuration.

## Application pages

| Page | Intended user | What it is for |
|---|---|---|
| `/` | Citizen | Analyze an issue photograph, prepare a complaint, submit it, and follow personal reports. |
| `/worker` | Worker | Review assigned reports, inspect evidence, and update report status with remarks. |
| `/admin` | Admin | Monitor the queue, manage user roles, assign reports, and view aggregate statistics. |

The backend checks the account role on protected routes. Hiding a page or a navigation link in the browser is not a security boundary.

## API reference

All protected endpoints require a valid Supabase access token in the request header:

```http
Authorization: Bearer YOUR_SUPABASE_ACCESS_TOKEN
```

The backend verifies the token and checks the user's active role and report ownership/assignment before processing protected operations.

### General and citizen endpoints

| Endpoint | Method | Access | Purpose |
|---|---|---|---|
| `/api/health` | GET | Public health check | Reports application/provider/database health information. |
| `/api/config` | GET | Public configuration | Returns frontend-safe Supabase URL and publishable key; never returns the secret key. |
| `/api/analyze` | POST | Application endpoint | Accepts an image and form fields for Gemini-based civic issue analysis. |
| `/api/auth/me` | GET | Authenticated | Returns the verified user's identity and active application role. |
| `/api/reports` | POST | Authenticated | Saves a citizen-reviewed report and its private evidence. |
| `/api/my-reports` | GET | Authenticated | Returns reports belonging to the signed-in user. |
| `/api/my-reports/{report_id}/history` | GET | Report owner | Returns status history for one of the user's reports. |
| `/api/public/statistics` | GET | Public aggregate data | Returns dashboard-level report statistics, not private report details. |

### Worker and administrator endpoints

| Endpoint | Method | Access | Purpose |
|---|---|---|---|
| `/api/staff/auth-check` | GET | Worker or admin | Checks staff portal access. |
| `/api/staff/reports` | GET | Worker or admin | Returns reports assigned to a worker, or the report queue for an admin. |
| `/api/staff/reports/{report_id}/history` | GET | Assigned worker or admin | Returns authorized status history for a report. |
| `/api/staff/reports/{report_id}/status` | PATCH | Assigned worker or admin | Changes report status and records a required remark. |
| `/api/admin/users` | GET | Admin | Lists users and application roles. |
| `/api/admin/users/{user_id}/role` | PATCH | Admin | Assigns the supported `citizen` or `worker` role. |
| `/api/admin/reports/{report_id}/assign` | PATCH | Admin | Assigns a report to an active worker. |

This is a project-level API overview, not a substitute for the request schemas and response models in the source code. Open `/docs` while the local server is running to inspect the API documentation generated by FastAPI.

## Security design

CivicPulse separates browser authentication from privileged database and storage operations.

- **Server-side token verification:** FastAPI verifies Supabase access tokens with Supabase Auth. The backend does not accept a role supplied by the browser as proof of authorization.
- **Role-based access control:** Protected routes check the active `citizen`, `worker`, or `admin` role.
- **Ownership checks:** Citizens can retrieve their own reports and report history, not another user's private records.
- **Assignment checks:** Workers can view and update only reports assigned to them. Administrators can manage the overall queue.
- **Private evidence storage:** The `civic-evidence` bucket is private. The API returns signed URLs only after checking the caller's access to the report.
- **Upload validation:** The report submission endpoint validates image type and size before storing evidence. The configured bucket also has upload restrictions.
- **Status audit trail:** Status changes and remarks are stored in `report_status_history` for traceability.
- **Secret isolation:** The Supabase secret key and Gemini API key are used on the server. Only the Supabase publishable key is returned to the browser.
- **Database protections:** The schema enables Row Level Security and limits direct browser access to application tables. The application uses the FastAPI server for privileged operations.

**Important security detail:** Supabase secret/service-role credentials have elevated privileges and can bypass Row Level Security. RLS being enabled does not make it safe to expose a secret key. Keep that key on the server, and preserve the backend's token, role, ownership, and assignment checks whenever routes are changed.

### Before using this beyond a controlled demo

The project is a hackathon prototype, not a security-audited public service. Before a real deployment, add and test production-grade controls such as request rate limiting, abuse protection/CAPTCHA where appropriate, structured security logging, monitored backups, key rotation procedures, dependency and vulnerability scanning, a stable HTTPS deployment, and a documented evidence-retention policy. Review access rules and test unauthorized citizen, worker, and admin requests before launch.

## Privacy, limitations and responsible use

- CivicPulse records are application records. They are not official government submissions or government-issued tracking numbers.
- Gemini's output is an AI-generated visual assessment. It is not a professional engineering inspection, an emergency assessment, or proof of the cause of damage.
- Department recommendations are suggestions. Verify the actual authority and jurisdiction before taking action.
- Citizens should review AI-generated text and correct inaccuracies before submitting a report.
- Images submitted for AI analysis are sent to the configured Gemini API. Images submitted with a saved report are also stored in the application's private Supabase evidence bucket. Configure provider accounts and storage retention appropriately for your use case.
- Do not upload identity documents, payment details, medical information, or unrelated photographs. Avoid including identifiable people, vehicle registration numbers, or other personal information unless it is necessary and you have a lawful reason to do so.
- Access to a private image is provided through a signed URL. Signed URLs are temporary access links; do not publish or share them publicly.
- Keep `.env`, OAuth client secrets, database passwords, and API keys private. Use `.env.example` only for variable names and placeholder values.

## Demo on another device

For a temporary demonstration, Cloudflare Quick Tunnel can expose the local FastAPI server over HTTPS.

1. Start CivicPulse locally using the command above.
2. Open a second PowerShell window and run:

```powershell
cloudflared tunnel --protocol http2 --url http://127.0.0.1:8000
```

3. Cloudflare prints a temporary URL ending in `trycloudflare.com`. Open that URL on the demo device.
4. Keep both the FastAPI terminal and the tunnel terminal running for the duration of the demo.
5. Add the current tunnel origin to Supabase Auth's allowed redirect URLs. For Google sign-in, also add the origin to the Google OAuth client's authorized JavaScript origins.

A Quick Tunnel URL is temporary and can change when the tunnel is restarted. It is suitable for a short demonstration, not permanent hosting. Do not expose a development server containing test accounts or sensitive data to the public internet without reviewing its security configuration.

## Ideas for pilots and future development

CivicPulse can be piloted in a limited, clearly defined environment before attempting a city-wide rollout.

### Practical pilot ideas

- **College or university campus:** Report damaged walkways, broken lights, overflowing bins, water leaks, and damaged facilities. Campus maintenance staff can act as workers and the facilities office can act as the administrator.
- **Apartment complex or gated community:** Residents submit maintenance issues; facility workers receive assignments and residents follow progress.
- **Ward-level civic pilot:** Work with a local civic group or municipal team to test report intake and internal triage for a small set of issue categories. Any real-world government workflow would require the relevant authority's approval and integration.
- **Public event or venue:** Give organizers a way to receive structured reports about waste, lighting, access routes, or damaged public facilities during an event.

### Potential next features

- Map view, geocoding, and location validation so administrators can group reports by area.
- Duplicate detection to identify multiple reports about the same pothole, leak, or damaged asset.
- Official department and jurisdiction lookup using verified government datasets.
- Notifications when a report is assigned, updated, or resolved.
- Response-time and resolution-time analytics for authorized administrators.
- Voice-based reporting and accessibility improvements.
- More Indian regional languages and better localization.
- Offline draft creation for locations with unreliable connectivity.
- Integration with official grievance systems where an authorized partnership and supported API exist.
- Configurable retention, export, and deletion tools for data administrators.

These are ideas for future work, not claims that the current prototype already provides those integrations.

## Troubleshooting

| Problem | What to check |
|---|---|
| Gemini analysis fails | Check `GEMINI_API_KEY`, the selected `GEMINI_MODEL`, API access, quota, and network connectivity. Restart FastAPI after editing `.env`. |
| Supabase configuration error | Verify `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_SECRET_KEY`; ensure there are no extra quotation marks or spaces. |
| Sign-in works but the app redirects incorrectly | Check the Supabase Site URL and allowed redirect URLs. Use the same local host consistently (`127.0.0.1` or `localhost`). |
| Google sign-in fails | Verify the Google Client ID/Secret in Supabase, the Supabase callback URI in Google Cloud, and the authorized JavaScript origin. |
| A new account cannot access `/worker` or `/admin` | New accounts are citizens by default. An admin must promote a worker; the first admin must be provisioned by the project owner. |
| Worker sees no assigned reports | Confirm the account has the `worker` role, `is_active` is true, and the administrator assigned a report to that user. |
| API returns `401 Unauthorized` | Sign in again and ensure the request includes a current `Authorization: Bearer ...` access token. |
| API returns `403 Forbidden` | The user may lack the required role, be inactive, or not own/be assigned to the requested report. |
| Evidence image cannot be opened | Confirm the `civic-evidence` bucket exists and is private, the report has an evidence path, and the signed URL is being generated after authorization. |
| Cloudflare shows an unavailable tunnel | Keep the FastAPI server running, keep the tunnel process open, and use the latest URL printed by `cloudflared`. |

## Acknowledgements

Built by **Ak and Yadav** as a hackathon prototype exploring how multimodal Generative AI can make civic reporting more structured, accessible, and actionable.

Thank you for checking out CivicPulse AI!
