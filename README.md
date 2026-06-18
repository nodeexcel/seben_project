# Seben CRM — Customer Intelligence Platform

Web-based CRM that processes WhatsApp conversations, emails, contacts, and PDF invoices into a centralized customer intelligence database.

**Current status:** M1–M4 complete. M5 (handoff) remaining.

## Milestones

| Phase | Status |
|---|---|
| M1 — Design & Prototype | **Complete** |
| M2 — Historical Data Processing | **Complete** |
| M3 — Communication Intelligence | In progress |
| M4 — CRM Application Completion | **Complete** |
| M5 — Final Delivery | Pending |

See `docs/milestones.md` for full detail, client sign-off, and scope decisions.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy |
| Parsing | pdfplumber, vobject, mailbox |
| Matching | rapidfuzz, phonenumbers |
| Invoices | Google Drive API (service account) |
| AI Summaries | OpenAI API (optional, M3) |
| Deploy | Docker Compose / AWS EC2 |

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — DATABASE_URL, CORS_ORIGINS, GOOGLE_DRIVE_CREDENTIALS_JSON
```

### 2. Start all services (Docker)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

### 3. Import data

**Google Drive invoices** (primary source):

```bash
cd backend && source venv/bin/activate
python scripts/sync_all_drive.py          # all years in config/drive_folders.json
python scripts/sync_all_drive.py 2026     # single year
```

**Local sample files** (WhatsApp, contacts, email, xlsx):

```bash
python scripts/import_samples.py
python scripts/cleanup_m2.py      # one-time / periodic data quality pass
```

**Scheduled Drive sync** (Mondays 6:00 AM):

```bash
# Already installed via cron — or run manually:
/home/ubuntu/seben_project/scripts/sync-drive-cron.sh
```

Or use **Upload & Extract** in the UI for one-off files.

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
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
│   │   ├── parsers/       # WhatsApp, email, contact, invoice, CRM xlsx
│   │   ├── schemas/       # Pydantic request/response models
│   │   └── services/      # Import, linking, drive sync, AI summary
│   └── scripts/
│       ├── sync_all_drive.py
│       ├── cleanup_m2.py
│       ├── import_samples.py
│       └── resync_contacts.py
├── config/
│   └── drive_folders.json # Year → Google Drive folder ID
├── frontend/src/
│   ├── api/
│   ├── components/
│   └── pages/             # Dashboard, Companies, Upload, Analytics
├── docs/
│   ├── architecture.md
│   ├── schema.md
│   └── milestones.md
├── secrets/               # google-drive.json (gitignored)
├── samples/               # Client sample data (gitignored)
└── uploads/               # Downloaded Drive PDFs (gitignored)
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/companies/` | List/search companies |
| GET | `/api/companies/{id}` | Company detail |
| POST | `/api/companies/` | Create company |
| PATCH | `/api/companies/{id}` | Update company |
| POST | `/api/companies/{id}/contacts` | Add contact |
| POST | `/api/companies/{id}/purchases` | Add purchase |
| POST | `/api/upload/` | Upload & extract file |
| POST | `/api/import/drive` | Sync invoices from Google Drive |
| GET | `/api/analytics/customers` | Revenue by customer |
| GET | `/api/analytics/products` | Sales by product |

## Upload Modes

- **Preview mode** (default): Parses file and returns extracted JSON without saving to DB
- **Persist mode**: Check "Save to database" to import contacts/companies into CRM

## Google Drive Invoice Layout

Client folder structure (one root folder per year):

```
YYYY Faturalar/
  ├── Tumay/
  │   └── MM. Month/
  │       └── shipment-folder/
  │           └── *.pdf
  ├── Zihni/
  ├── HTF/
  └── Öyküm/
```

Share each year folder with the service account email as **Viewer**. Add new years to `config/drive_folders.json`.

## Client Sign-off (M1)

| Item | Status |
|---|---|
| Database schema | Approved |
| UI / UX | Approved |
| Invoice ingestion via Drive | Approved |
| OCR for scanned PDFs | Not required — text-based PDFs from producers |
| Login / authentication | Not in scope |

## Environment Variables

See `.env.example`. Key variables:

- `DATABASE_URL` — PostgreSQL connection string
- `GOOGLE_DRIVE_CREDENTIALS_JSON` — Path to service account JSON key
- `CORS_ORIGINS` — Allowed frontend origins
- `OPENAI_API_KEY` — Optional, for AI summaries (M3)

## Documentation

- `docs/architecture.md` — system design and data flow
- `docs/schema.md` — tables, fields, linking rules
- `docs/milestones.md` — milestone status and client decisions
