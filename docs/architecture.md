# System Architecture — Seben CRM

## Overview

Seben CRM is a self-hosted customer intelligence platform that ingests multi-source business data, links records to unified company profiles, and exposes search, analytics, and manual editing through a web interface.

**M1 (Design & Prototype) is complete.** Schema and UI are client-approved. See `milestones.md` for current phase status.

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│  Dashboard · Companies · Upload · Analytics · Company Profile   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │ Parsers  │  │ Linking  │  │ Import   │  │ Drive Sync      │ │
│  │ Layer    │  │ Service  │  │ Service  │  │ (Google Drive)  │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SQLAlchemy ORM
┌──────────────────────────▼──────────────────────────────────────┐
│                      PostgreSQL                                 │
│  companies · contacts · purchases · products · interactions     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Upload & Extract

```
User uploads file (or CLI / Drive sync)
    → API detects source type (.txt, .pdf, .vcf, .eml, .xlsx)
    → Parser extracts structured data
    → Preview returned to UI (JSON) OR persisted to database
```

### 2. Google Drive Invoice Sync (M2 — primary invoice source)

```
sync_all_drive.py reads config/drive_folders.json
    → Service account lists year folder → supplier subfolders
    → Recursively collects PDFs (month/shipment nested folders)
    → Downloads to uploads/drive/{year}/
    → Invoice parser + linking pipeline
    → supplier_name from folder name; dedup by drive_file_id
```

### 3. Entity Linking

```
Extracted contact/company
    → Normalize phone (E.164) and email (lowercase)
    → Fuzzy match company names (rapidfuzz, threshold 85%)
    → Match contacts by exact email or phone
    → Link or create company profile
    → Attach purchases, interactions, product interests
```

### 4. CRM Queries (M4)

```
User searches/filters
    → API queries PostgreSQL with joins
    → Returns company profiles, analytics, timelines
    → Manual edits update records directly (UI in progress)
```

## Parser Layer

| Source | Format | Parser | Extracts |
|---|---|---|---|
| WhatsApp | `.txt` | `parsers/whatsapp.py` | Messages, participants, chat title |
| Contacts | `.vcf`, `.csv` | `parsers/contacts.py` | Name, email, phone, organization |
| Email | `.eml`, `.mbox` | `parsers/email_parser.py` | Sender, subject, body, date |
| Invoice | `.pdf` | `parsers/invoice.py` | Company, contacts, line items, totals |
| CRM | `.xlsx` | `parsers/crm_xlsx.py` | Companies, contacts, interests |

Parsers return a unified `ExtractionOutput` dataclass regardless of source type.

**PDF invoices:** Text extraction via `pdfplumber`. **OCR is not in scope** — the client will obtain text-based PDFs from producers for any scanned documents. Image-only PDFs are skipped with a warning.

## Matching Strategy

Entity resolution uses a tiered approach:

1. **Exact match** — Normalized email or phone number
2. **Fuzzy match** — Company name similarity ≥ 85% (rapidfuzz token_sort_ratio)
3. **Manual merge** — User corrects links in CRM UI (Milestone 4)

## Database Design

See `schema.md` for full field definitions. Core entities:

- **companies** — Central customer profile
- **contacts** — People linked to companies
- **products** — Product catalog (Fresh/Frozen categories)
- **purchases** — Transaction records from invoices (includes `supplier_name`)
- **product_interests** — Products mentioned in communications
- **interactions** — WhatsApp messages, emails, manual notes
- **documents** — Source file tracking (`drive_file_id`, `invoice_year`, `supplier_name`)

## API Design

RESTful JSON API served by FastAPI with auto-generated OpenAPI docs at `/docs`.

No login or authentication layer — not required by the client for this project.

## Deployment

**Development:** Docker Compose (postgres, backend, frontend).

**Production (current):** AWS EC2 — PostgreSQL, uvicorn backend, pm2 frontend. Google Drive credentials in `secrets/` (gitignored).

## M1 Deliverables Checklist ✅

- [x] System architecture document
- [x] Database schema design
- [x] CRM field definitions
- [x] Full parsers for all data sources (not stubs)
- [x] Sample extraction via Upload UI
- [x] Docker Compose development environment
- [x] Client sample data analysis
- [x] Schema approval from client
- [x] Prototype demo with real data
- [x] UI/UX approval from client

## Client Scope Decisions

| Topic | Decision |
|---|---|
| Invoice ingestion | Google Drive folders (not Gmail) |
| Scanned PDFs | No OCR — client requests text-based PDFs from producers |
| Authentication | Not in scope |
| UI | Approved as built |

## Technology Choices

| Choice | Rationale |
|---|---|
| FastAPI | Fast to build, great for file uploads, auto API docs |
| PostgreSQL | Relational data with complex joins for analytics |
| React + Vite | Lightweight SPA, fast dev experience |
| pdfplumber | Reliable text extraction from text-based PDF invoices |
| Google Drive API | Client’s existing invoice archive; supplier = subfolder name |
| rapidfuzz | Fast fuzzy string matching for company names |
| phonenumbers | International phone normalization (E.164) |
| Docker Compose | Simple self-hosted deployment for client |
