# DEV NOTES

Personal development notes and local setup commands for the Job Tracker App.

---

# Project Structure
```txt
job-tracker/
├── backend/
│   ├── app/
│   ├── __tests__/
│   ├── credentials/
│   ├── token/
│   └── requirements.txt
├── frontend/
└── .venv/
```

---

# Python Virtual Environment

Activate venv from project root:
```bash
source .venv/bin/activate
```

Deactivate:
```bash
deactivate
```

---

# Running Backend

From project root:

```bash
PYTHONPATH=. uvicorn backend.app.main:app --reload
```

Backend runs at:
```txt
http://127.0.0.1:8000
```

Swagger docs:
```txt
http://127.0.0.1:8000/docs
```

---

# Running Frontend

```bash
cd frontend
npm run dev
```

Frontend runs at:
```txt
http://127.0.0.1:5173
```

---

# Backend Testing

Run all backend tests:
```bash
PYTHONPATH=. pytest backend/__tests__ -v
```

Run backend coverage:
```bash
PYTHONPATH=. pytest backend/__tests__ --cov=backend.app --cov-report=term-missing
```

Generate HTML coverage report:
```bash
PYTHONPATH=. pytest backend/__tests__ --cov=backend.app --cov-report=html
```

Open coverage report:
```bash
open htmlcov/index.html
```

---

# Frontend Testing

Run frontend tests:
```bash
cd frontend
npm test
```

Run frontend coverage:
```bash
cd frontend
npm run test -- --coverage
```

Open frontend coverage:
```bash
open coverage/index.html
```

---

# Gmail OAuth Notes

Credentials location:
```txt
backend/credentials/credentials.json
```

Stored token:
```txt
backend/token/gmail_token.json
```
Check token expiry:
```bash
cat backend/token/gmail_token.json | grep expiry
```

Check refresh token exists:
```bash
cat backend/token/gmail_token.json | grep refresh_token
```

Re-authorize Gmail:
```txt
http://127.0.0.1:8000/gmail/auth/url
```

---

# Important .gitignore Entries

```gitignore
.venv/
coverage/
htmlcov/
backend/token/
backend/credentials/
.env
.pytest_cache/
```

---

# Common Commands

Install frontend packages:
```bash
cd frontend
npm install
```

Install backend packages:
```bash
pip install -r backend/requirements.txt
```

Freeze backend requirements:
```bash
pip freeze > backend/requirements.txt
```

---

# Useful URLs

Frontend:
```txt
http://127.0.0.1:5173
```

Backend:
```txt
http://127.0.0.1:8000
```

Swagger Docs:
```txt
http://127.0.0.1:8000/docs
```