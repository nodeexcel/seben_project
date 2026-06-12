# System Architecture — Seben CRM

## Overview

Seben CRM is a self-hosted customer intelligence platform that ingests multi-source business data, links records to unified company profiles, and exposes search, analytics, and manual editing through a web interface.

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│  Dashboard · Companies · Upload · Analytics · Company Profile   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │ Parsers  │  │ Linking  │  │ Import   │  │ AI Summary      │ │
│  │ Layer    │  │ Service  │  │ Service  │  │ (OpenAI)        │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SQLAlchemy ORM
┌──────────────────────────▼──────────────────────────────────────┐
│                      PostgreSQL                                 │
│  companies · contacts · purchases · products · interactions     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Upload & Extract (Phase 1 — Current)

```
User uploads file
    → API detects source type (.txt, .pdf, .vcf, .eml, etc.)
    → Parser extracts structured data
    → Preview returned to UI (JSON)
    → [Optional] Persist mode saves to database
```

### 2. Entity Linking (Milestone 2–3)

```
Extracted contact/company
    → Normalize phone (E.164) and email (lowercase)
    → Fuzzy match company names (rapidfuzz, threshold 85%)
    → Match contacts by exact email or phone
    → Link or create company profile
    → Attach purchases, interactions, product interests
```

### 3. CRM Queries (Milestone 4)

```
User searches/filters
    → API queries PostgreSQL with joins
    → Returns company profiles, analytics, timelines
    → Manual edits update records directly
```

## Parser Layer

| Source | Format | Parser | Extracts |
|---|---|---|---|
| WhatsApp | `.txt` | `parsers/whatsapp.py` | Messages, participants, chat title |
| Contacts | `.vcf`, `.csv` | `parsers/contacts.py` | Name, email, phone, organization |
| Email | `.eml`, `.mbox` | `parsers/email_parser.py` | Sender, subject, body, date |
| Invoice | `.pdf` | `parsers/invoice.py` | Company, contacts, line items, totals |

Parsers return a unified `ExtractionOutput` dataclass regardless of source type. This allows the import service to process any source through the same pipeline.

**Note:** Invoice parser uses text extraction (`pdfplumber`). Scanned/image PDFs require OCR (planned for Milestone 2 if client data requires it).

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
- **purchases** — Transaction records from invoices
- **product_interests** — Products mentioned in communications
- **interactions** — WhatsApp messages, emails, manual notes
- **documents** — Source file tracking and extraction audit trail

## API Design

RESTful JSON API served by FastAPI with auto-generated OpenAPI docs at `/docs`.

Authentication is not implemented in Phase 1. Will be added before production handoff if required by client.

## Deployment

Docker Compose with three services:

| Service | Image | Port |
|---|---|---|
| `db` | postgres:16-alpine | 5432 |
| `backend` | Custom Python 3.12 | 8000 |
| `frontend` | Custom Node 20 | 5173 |

Client self-hosts on any machine with Docker installed. No cloud dependency except optional OpenAI API for summaries.

## Future Upload Workflow (Milestone 5)

```
User drops new files in Upload UI
    → Files stored in uploads/
    → Parser + linking pipeline runs
    → New records merged into existing profiles
    → Document audit trail maintained
```

## Phase 1 Deliverables Checklist

- [x] System architecture document
- [x] Database schema design
- [x] CRM field definitions
- [x] Parser stubs for all 4 data sources
- [x] Sample extraction via Upload UI
- [x] Docker Compose development environment
- [ ] Client sample data analysis (waiting on client)
- [ ] Schema approval from client
- [ ] Prototype demo with real sample files

## Technology Choices

| Choice | Rationale |
|---|---|
| FastAPI | Fast to build, great for file uploads, auto API docs |
| PostgreSQL | Relational data with complex joins for analytics |
| React + Vite | Lightweight SPA, fast dev experience |
| pdfplumber | Reliable text extraction from PDF invoices |
| rapidfuzz | Fast fuzzy string matching for company names |
| phonenumbers | International phone normalization (E.164) |
| Docker Compose | Simple self-hosted deployment for client |
