# Clinical Lab Insight

AI-powered laboratory result interpretation and verified doctor second opinions for Nigerians.

## Core Features


## Tech Stack


## User Roles


## Project structure

This section shows the main folders and files in the repository so you can
find API routes, configuration, migrations, and tests quickly.

```text
.
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── router.py
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
├── alembic.ini
├── pyproject.toml
└── README.md
```
# Clinsights — Backend (Local Run)

This README explains how to run the backend locally for development and testing. It covers creating a virtual environment, installing dependencies, running the API server and running the Celery worker manually (no .bat files, no wrappers). It also lists the main endpoints you'll use when testing.

Prerequisites
- Python 3.10+ (3.11/3.12/3.13 supported)
- PostgreSQL running and accessible via `DATABASE_URL`
- A Redis instance for Celery (Upstash/redis) — `REDIS_URL`
- Network access for Gemini API (if using AI features)

Workspace layout (relevant)
- `app/` — FastAPI app
- `celery_app.py` — Celery app entrypoint
- `tests/` — test scripts (includes `tests/test_endpoints.py`)
- `lab_results.png` — example test image
- `.env` — environment variables (not checked in)

1. Create & activate a virtual environment

Windows (Command Prompt):
```bat
cd C:\Users\Sumayyah\Desktop\project\HNGTASK5\backend
python -m venv .venv
.venv\Scripts\activate.bat
```

Windows (PowerShell):
```powershell
cd C:\Users\Sumayyah\Desktop\project\HNGTASK5\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:
```bash
cd ~/Desktop/project/HNGTASK5/backend
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

This project uses `pyproject.toml` for packaging. Install editable install or a requirements file if you maintain one.

```bash
pip install -e .
# or, if you have a requirements.txt
pip install -r requirements.txt
```

3. Create a local `.env` file

At minimum add these entries to `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/clin_db
REDIS_URL=rediss://default:YOUR_REDIS_URL:6379
GEMINI_API_KEY=your_gemini_api_key_here
UPLOAD_DIR=uploads
```

4. Run the API server (development)

Open a terminal, activate the venv (step 1), then run:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Expected output (partial):

```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
```

5. Run the Celery worker (manual, separate terminal)

Open a new terminal, activate the same venv, then start the worker. Use the same interpreter as the API server.

Command Prompt / PowerShell (Windows):
```powershell
cd C:\Users\Sumayyah\Desktop\project\HNGTASK5\backend
.\.venv\Scripts\Activate.ps1   # or activate.bat on cmd
python -m celery -A celery_app worker --pool=solo --loglevel=info -Q analysis -n analysis@%COMPUTERNAME%
```

macOS / Linux:
```bash
cd ~/Desktop/project/HNGTASK5/backend
source .venv/bin/activate
python -m celery -A celery_app worker --pool=solo --loglevel=info -Q analysis -n analysis@$(hostname)
```

Worker output will show queue and readiness:

```
analysis@HOSTNAME ready.
[tasks]
	. app.services.tasks.process_analysis
```

6. Run the tests (optional)

In a third terminal (activate venv first):

PowerShell:
```powershell
cd C:\Users\Sumayyah\Desktop\project\HNGTASK5\backend
$env:TEST_BASE='http://127.0.0.1:8001'
python tests/test_endpoints.py
```

Command Prompt:
```bat
cd C:\Users\Sumayyah\Desktop\project\HNGTASK5\backend
set TEST_BASE=http://127.0.0.1:8001
python tests/test_endpoints.py
```

7. Key endpoints (for Insomnia / curl)

- Health check:

```bash
curl http://127.0.0.1:8001/api/v1/health
# expected: {"status":"ok"}
```

- Upload (form-data file):

```bash
curl -X POST http://127.0.0.1:8001/api/v1/analysis/upload \
	-F "file=@lab_results.png"
```

- Check status:

```bash
curl http://127.0.0.1:8001/api/v1/analysis/<analysis_id>/status
```

- Get full results (when status completed):

```bash
curl http://127.0.0.1:8001/api/v1/analysis/<analysis_id>
```

8. Recommended local workflow

1. Start Postgres and Redis (or ensure accessible)
2. Activate venv and install deps
3. Start API server in terminal A
4. Start Celery worker in terminal B
5. Run tests or use Insomnia in terminal C

9. Troubleshooting

- "Event loop is closed" or async DB errors:
	- Make sure both the API and worker use the same project venv Python (activate `.venv` before running commands).
	- Avoid running the worker with a different interpreter (Conda vs venv).

- Worker connects to wrong Redis URL:
	- Ensure `REDIS_URL` is present in `backend/.env`
	- Restart the worker after changing `.env` because Celery reads env at import time

- Gemini errors or invalid JSON:
	- Verify `GEMINI_API_KEY` is set in `.env`
	- Inspect Celery worker logs for details about structured-output or schema failures

10. Notes

- This README intentionally omits Windows `.bat` helpers; use the commands above directly in separate terminals for manual control.
- If you prefer convenience scripts, see `START_SERVICES.ps1` or `START_SERVICES.bat` in the repo root — but they are optional.

If anything here is unclear or you want a shorter quickstart, tell me which shell you use (cmd / PowerShell / bash) and I will provide a one-liner copy-paste section for that shell.

1. Fork the repository and create your feature branch (`git checkout -b feature/your-feature`)
2. Install dependencies: `uv sync`
3. Run tests before committing: `uv run pytest`
4. Install pre-commit hook (`uv run pre-commit install`)
5. Commit your changes (`git commit -m 'Add feature'`)
6. Push to your branch (`git push origin feature/your-feature`)
7. Open a Pull Request

### Guidelines

- Follow existing code style and conventions
- Write clear, descriptive commit messages
- Include tests for new features
- Keep PRs focused and manageable in size
- Never commit secrets, keys, or credentials
