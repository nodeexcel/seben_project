# Project Milestones — Seben CRM

**Client:** Happy Table Foods  
**Last updated:** June 2026

---

## Summary

| Milestone | Status | Notes |
|---|---|---|
| **M1 — Design & Prototype** | **Complete** | Schema + UI signed off by client |
| **M2 — Historical Data Processing** | **Complete** | Drive 2022–2026, cleanup done |
| **M3 — Communication Intelligence** | Pending | WhatsApp/email samples in; full timeline UI pending |
| **M4 — CRM Application Completion** | **Complete** | Search, edit, merge, timeline |
| **M5 — Final Delivery** | Pending | Live on server; handoff + automation pending |

---

## M1 — Design & Prototype ✅ Complete

### Deliverables

- [x] System architecture (`docs/architecture.md`)
- [x] Database schema (`docs/schema.md`)
- [x] CRM field mapping aligned with client spec
- [x] Full parser layer (WhatsApp, email, contacts, invoice PDF, CRM xlsx)
- [x] Entity linking service (phone, email, fuzzy company names)
- [x] React UI: Dashboard, Companies, Company Detail, Upload, Analytics
- [x] FastAPI REST API with OpenAPI docs
- [x] Docker Compose development environment
- [x] Prototype deployed and demoed with real client data
- [x] Client sign-off on schema and UI/UX

### Client decisions (M1 sign-off)

| Topic | Decision |
|---|---|
| **Schema & fields** | Approved — see `docs/schema.md` |
| **UI / UX** | Approved — current layout and navigation confirmed |
| **Invoice source** | Google Drive only (year folders → supplier subfolders → PDFs). Not Gmail. |
| **Scanned PDFs / OCR** | **Not required.** Client will ask producers for text-based PDFs going forward. |
| **Login / authentication** | **Out of scope** — not requested for this project. |

---

## M2 — Historical Data Processing ✅ Complete

### Done

- [x] Google Drive service account integration
- [x] Year folder config (`config/drive_folders.json`) — 2022 through 2026
- [x] Recursive sync (supplier → month → shipment subfolders)
- [x] Supplier name on purchases from Drive folder name
- [x] Deduplication by `drive_file_id`
- [x] Sample data import (WhatsApp, contacts, email, CRM xlsx) via CLI
- [x] Contact resync and duplicate-company merge script
- [x] Supplier name normalization (Tumay / Tümay / HTF aliases)
- [x] Invoice parser: skip CMR/packing docs; cleaner product names
- [x] M2 data cleanup script (`backend/scripts/cleanup_m2.py`)
- [x] Scheduled Drive sync (`scripts/sync-drive-cron.sh` — Mondays 6:00)

### Acceptance criteria met

- Companies visible in CRM with purchase history from full Drive import (8,783 PDFs, 2022–2026)
- Contacts imported from phone list and linked to companies
- Purchase history generated from invoice dataset with supplier column

### Explicitly not in scope

- OCR for image-based PDFs (client declined — text PDFs from producers instead)

---

## M3 — Communication Intelligence (pending)

### Done (backend)

- [x] WhatsApp and email parsers
- [x] Interactions and product interests stored in database
- [x] Fresh/Frozen product detection from text

### Pending

- [ ] Full historical WhatsApp/email import (if client provides exports)
- [ ] Optional AI customer summaries (OpenAI — not started)

### Done in UI (via M4)

- [x] Communication timeline on company profile

---

## M4 — CRM Application Completion ✅ Complete

### Done

- [x] Company search and filters
- [x] Company profile (contacts, purchases with supplier, product interests)
- [x] Purchase analytics (by customer and product)
- [x] Backend APIs for create/update company and add contact/purchase
- [x] Edit company notes, country, and category in UI
- [x] Add, edit, and delete contacts in UI
- [x] Manual merge of duplicate companies
- [x] Communication timeline (WhatsApp / email) on company profile

### Acceptance criteria met

- User can query and view customer information through the application
- User can manually correct profile data and contacts
- User can merge duplicate company records

---

## M5 — Final Delivery (pending)

### Done

- [x] Application running on client AWS server with production data

### Pending

- [ ] Automated Drive sync and monitoring
- [ ] Client handoff documentation (adding new years, routine use)
- [ ] Database backup procedure
- [ ] Final acceptance testing

### Out of scope (per client)

- User authentication / login system
- OCR pipeline
