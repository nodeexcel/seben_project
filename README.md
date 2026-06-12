# Seben CRM — Customer Intelligence Platform

Web-based CRM that processes WhatsApp conversations, emails, contacts, and PDF invoices into a centralized customer intelligence database.

**Current status:** Phase 1 prototype (architecture, database schema, extraction parsers, basic UI)

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy |
| Parsing | pdfplumber, vobject, mailbox |
| Matching | rapidfuzz, phonenumbers |
| AI Summaries | OpenAI API (optional) |
| Deploy | Docker Compose |

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

### 3. Place client sample files

Put sample data in the `samples/` folder (gitignored):

```
samples/
├── whatsapp/     # .txt exports
├── contacts/     # .vcf, .csv
├── emails/       # .eml, .mbox
└── invoices/     # .pdf
```

Then test extraction at **Upload & Extract** in the UI.

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Requires PostgreSQL running (see .env.example for DATABASE_URL)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
seben_project/
├── backend/
│   ├── app/
│   │   ├── api/           # REST endpoints
│   │   ├── models/        # SQLAlchemy models
│   │   ├── parsers/       # WhatsApp, email, contact, invoice parsers
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # Import, linking, AI summary
│   │   └── utils/         # Normalization & fuzzy matching
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/           # API client
│       ├── components/    # Layout, shared UI
│       └── pages/         # Dashboard, Companies, Upload, Analytics
├── docs/
│   ├── architecture.md
│   └── schema.md
├── samples/               # Client sample data (gitignored)
├── uploads/               # Uploaded files (gitignored)
└── docker-compose.yml
```

## API Endpoints (Phase 1)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/companies/` | List/search companies |
| GET | `/api/companies/{id}` | Company detail |
| POST | `/api/companies/` | Create company |
| POST | `/api/upload/` | Upload & extract file |
| GET | `/api/analytics/customers` | Revenue by customer |
| GET | `/api/analytics/products` | Sales by product |

## Upload Modes

- **Preview mode** (default): Parses file and returns extracted JSON without saving to DB
- **Persist mode**: Check "Save to database" to import contacts/companies into CRM

## Milestones

| Phase | Status |
|---|---|
| M1 — Design & Prototype | In progress |
| M2 — Historical Data Processing | Pending |
| M3 — Communication Intelligence | Pending |
| M4 — CRM App Completion | Pending |
| M5 — Final Delivery | Pending |

See `docs/architecture.md` and `docs/schema.md` for full technical design.

## Environment Variables

See `.env.example` for all options. Key variables:

- `DATABASE_URL` — PostgreSQL connection string
- `OPENAI_API_KEY` — Optional, for AI customer summaries
- `CORS_ORIGINS` — Allowed frontend origins
