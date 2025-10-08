# 🧭 Job Application Tracker

A full-stack web application designed to help job seekers organize, visualize, and track their job applications efficiently.

---

## 🚀 Overview

The **Job Application Tracker** provides a personal dashboard for managing every aspect of the job search process — from saving job postings to tracking application statuses, follow-ups, and interviews.

It aims to:
- Reduce manual tracking (spreadsheets, notes)
- Visualize your job search metrics
- Automatically sync with job boards and emails (future)
- Support resume and job-description management per application

---

## 🧩 Tech Stack

**Frontend**
- React (TypeScript)
- Vite
- Tailwind CSS (v4)
- Axios
- Vitest + React Testing Library (for unit/integration testing)

**Backend**
- FastAPI (Python)
- SQLAlchemy ORM + Alembic (for migrations)
- SQLite (local dev) → PostgreSQL (production)
- Pydantic schemas for validation
- Pytest for backend testing

---

## 📸 Features (MVP)

- ✅ Add, edit, and delete job applications  
- ✅ Responsive, modern UI built with Tailwind CSS  
- ✅ Persistent database (SQLite/PostgreSQL)  
- ✅ Form validation with contextual feedback  
- ✅ Modular component architecture  
- ✅ Frontend & backend unit tests  
- ✅ Dynamic job list with sorting & status tracking  

---

## 🎯 Roadmap (In Progress)

| Feature | Status |
|----------|---------|
| 📊 Dashboard Metrics (Applied, Interviewing, Offers, Rejected) | 🔧 In Progress |
| 📆 Follow-up Reminders / To-do List | 🧠 Planned |
| 📩 Email Integration (Auto-import applications) | 🧠 Planned |
| 🌐 Job Board Scraper (LinkedIn, Indeed, Google Jobs) | 🧠 Planned |
| 🗂️ Resume/Job Description Attachment | 🧠 Planned |
| 🔒 Authentication & Multi-user Support | 🧠 Planned |
| ☁️ Cloud Deployment (Render / Vercel + Supabase) | 🧠 Planned |

---

## 🧪 Testing

**Frontend:**  
- Unit tests with Vitest & React Testing Library  
- Coverage reports (`npm run test -- --coverage`)  
- Mocked API layer (no real backend calls during testing)

**Backend:**  
- Pytest with in-memory SQLite for isolation  
- Automated validation of CRUD routes

---

## 🧰 Setup Instructions


### 🖥️ Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### 🌐 Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the app in your browser at `http://127.0.0.1:5173`.

---

## 🧭 API Endpoints (MVP)

| Method | Endpoint | Description |
|--------|-----------|-------------|
| `GET` | `/jobs/` | List all jobs |
| `POST` | `/jobs/` | Create a new job |
| `GET` | `/jobs/{id}` | Get job details |
| `PUT` | `/jobs/{id}` | Update job |
| `DELETE` | `/jobs/{id}` | Delete job |
| `GET` | `/jobs/search` | Search by company, title, or location |

---

## 🧠 Design Philosophy

This project emphasizes:
- **Scalability:** Clear folder structure for both backend and frontend  
- **Maintainability:** Modularized components and consistent naming  
- **Testability:** Unit tests written for each layer  
- **User Experience:** Minimalist, responsive UI with contextual hints  

---

## 🖼️ UI Preview

*(Insert your screenshot here once you’re ready)*

---

## 🤝 Contributing

1. Fork the repo  
2. Create a new branch (`feature/add-graph-widget`)  
3. Commit your changes  
4. Push and open a Pull Request  

---

## 🧑‍💻 Author

**Anand Rai**  
📍 Pittsburgh, PA  
🎓 B.S. Computer Science, California State University, Sacramento  
💼 Software Engineer — passionate about full-stack development, fintech, and creative UX  
🎵 Also a musician in his free time!

---

## 🪶 License

MIT License © 2025 Anand Rai

---

## 🧭 Project Status

🟢 **Active Development** — The core backend and frontend integration are complete.  
Next milestones include metric visualization, job import automation, and cloud deployment.

## Development Roadmap
- [x] CRUD functionality
- [x] Job form modal
- [x] Multi-job upload
- [ ] Dashboard analytics (charts)
- [ ] Resume upload per job
- [ ] Email/job scraping automation