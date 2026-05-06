# Job Tracker App

A full-stack job application tracking platform focused on improving the quality and organization of the software engineering job search process.

The project began as a personal job application tracker and is gradually evolving into a workflow automation platform that combines:
- application tracking
- resume tailoring
- email parsing
- job discovery
- analytics and follow-up management

The current focus is building a stable and well-tested MVP before expanding into broader automation features.

---

## Current Stack

### Frontend
- React
- TypeScript
- Vite
- TailwindCSS
- React Router
- Vitest + React Testing Library

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL / SQLite (development)
- Gmail API integration
- Pytest

---

## Current Features

### Job Management
- Create, edit, update, and delete job applications
- Batch upload jobs
- Track:
  - company
  - title
  - location
  - status
  - application dates
  - follow-up dates
  - notes
  - job links
  - source/platform

### Search & Filtering
- Search jobs by:
  - title
  - company
  - location
  - status
- Sorting and pagination support

### Frontend UI
- Dashboard page
- Dedicated jobs page
- Modal-based job creation/editing
- Responsive job table
- Upload jobs modal
- Dashboard metrics cards

### Gmail Integration (In Progress)
- Google OAuth authentication
- Gmail API connection
- Fetching and parsing job-related emails
- Experimental email classification pipeline
- Planned:
  - automatic application detection
  - application status updates from emails
  - duplicate prevention using parsed email logs

### Testing
- Component testing with Vitest and React Testing Library
- Backend API testing with Pytest
- Coverage tracking enabled

---

## Current Development Focus

The current phase of the project is focused on:
1. Stabilizing the existing architecture
2. Improving automated test coverage
3. Refining Gmail parsing and classification
4. Building a more complete dashboard experience
5. Improving data quality and application workflows

---

## Planned Features

### Application Automation
- Gmail-based application syncing
- Automatic status updates
- Follow-up reminders

### Resume Tailoring
- AI-assisted tailored resume generation
- Cover letter generation
- Version history for generated documents

### Job Discovery
- External job API integrations
- Job fit scoring
- Personalized recommendation feed

### Analytics
- Application trends
- Interview conversion tracking
- Response-rate metrics
- Weekly summaries

---

## Project Status

This project is actively under development and currently serves as both:
- a production-quality personal workflow tool
- a long-term full-stack systems design project

The focus is currently on architecture, reliability, testing, and scalable feature design rather than rapid feature expansion.