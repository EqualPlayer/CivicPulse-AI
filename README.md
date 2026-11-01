# CivicPulse AI — Hackathon MVP starter

A small FastAPI + HTML/CSS/JS prototype for multimodal civic-issue triage. Citizens upload a photo, receive a structured AI analysis and complaint draft, review/edit it, and save it to a database.

## Important truthfulness and safety boundaries

- AI severity is a preliminary estimate from the submitted image, not an emergency assessment.
- Department suggestions are broad guidance. The exact authority must be verified for the user's jurisdiction.
- Saving creates a CivicPulse application record only. It does **not** file a complaint with a government authority.
- The dashboard reads persisted rows from SQLite or Supabase; it contains no seeded mock records.
- The app does not retain the uploaded image in this first version. The image is sent to the selected AI provider for analysis.

## 1. Requirements

- Python 3.10+
- A Gemini API key (recommended first) or OpenAI API key
- Optional Supabase project for a hosted PostgreSQL database

## 2. Setup on Windows (PowerShell)

Open PowerShell in this folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` in VS Code / Notepad and add your key. Start with:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_real_key_here
```

Do not put API keys in `static/app.js`, HTML, GitHub, screenshots, or this chat.

Run:

```powershell
uvicorn app:app --reload
```

Open http://127.0.0.1:8000

## 3. API keys

- Gemini: https://aistudio.google.com/api-keys
- OpenAI: https://platform.openai.com/api-keys

Gemini is the suggested first provider for this sprint. OpenAI API usage is billed separately from ChatGPT. Check the provider's current pricing and usage limits before use.

To switch providers, set `AI_PROVIDER=gemini` or `AI_PROVIDER=openai` in `.env`, and set the corresponding API key. Restart the server after changing `.env`.

Model IDs can be changed in `.env` with `GEMINI_MODEL` and `OPENAI_MODEL` if your account does not have access to the defaults.

## 4. Supabase hosted database (recommended before final deployment)

1. Create a Supabase project.
2. Open SQL Editor and run `schema.sql`.
3. In Project Settings > API, copy the Project URL and service-role key.
4. Put them in `.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVER_ONLY_SERVICE_ROLE_KEY
```

5. Restart the app. `/api/health` should report `supabase` as the database mode.

The service-role key must remain on the server. Never expose it to browser JavaScript or commit `.env`.

Without Supabase credentials, the app uses a local SQLite database (`civicpulse.db`) so you can build and test locally. For a public deployment, use Supabase rather than ephemeral local storage.

## 5. Endpoints

- `GET /api/health` — backend / provider / database health
- `POST /api/analyze` — multimodal image analysis (multipart form)
- `POST /api/reports` — persist a citizen-approved report
- `GET /api/reports` — retrieve actual saved reports

## 6. Architecture

```text
Browser (HTML/CSS/JS)
    | multipart image + location + description + language
    v
FastAPI /api/analyze
    |
    +--> Gemini Interactions API (multimodal + JSON schema)
    |        OR
    +--> OpenAI Responses API (image input + JSON schema)
    |
    v
Citizen reviews/edits draft in browser
    |
    v
FastAPI /api/reports
    |
    +--> Supabase PostgreSQL (hosted)
    |        OR
    +--> SQLite (local development fallback)
    |
    v
GET /api/reports --> live dashboard
```

## 7. Before the judges' demo

- Use a real photo of a civic issue and an accurate location.
- Make one test report, then confirm it appears in Supabase and the dashboard.
- Verify `/api/health` reports the expected AI provider and database mode.
- Keep your API keys on the server.
- Explain clearly that this prototype prepares and tracks reports inside CivicPulse; it does not submit them to a government grievance portal.
- Test a blurry / unrelated image and an API failure before the demo.
