# Project Milestones — Seben CRM

**Client:** Happy Table Foods  
**Last updated:** June 2026

---

## Summary

| Milestone | Status | Notes |
|---|---|---|
| **M1 — Design & Prototype** | **Complete** | Schema + UI signed off by client |
| **M2 — Historical Data Processing** | In progress | Drive invoices 2022–2026 imported |
| **M3 — Communication Intelligence** | Pending | WhatsApp/email samples in; full timeline UI pending |
| **M4 — CRM App Completion** | Pending | View/search done; edit/merge UI pending |
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

## M2 — Historical Data Processing (in progress)

### Done

- [x] Google Drive service account integration
- [x] Year folder config (`config/drive_folders.json`) — 2022 through 2026
- [x] Recursive sync (supplier → month → shipment subfolders)
- [x] Supplier name on purchases from Drive folder name
- [x] Deduplication by `drive_file_id`
- [x] Sample data import (WhatsApp, contacts, email, CRM xlsx) via CLI
- [x] Contact resync and duplicate-company merge script

### Pending

- [ ] Data quality pass (supplier name normalization, contact noise from CMR docs)
- [ ] Invoice parser tuning (line items / product column accuracy)
- [ ] Scheduled Drive sync (cron)
- [ ] Broader duplicate company cleanup

### Explicitly not in scope

- OCR for image-based PDFs (client declined — text PDFs from producers instead)

---

## M3 — Communication Intelligence (pending)

### Done (backend)

- [x] WhatsApp and email parsers
- [x] Interactions and product interests stored in database
- [x] Fresh/Frozen product detection from text

### Pending

- [ ] Communication timeline on company profile (UI)
- [ ] Full historical WhatsApp/email import (if client provides exports)
- [ ] Optional AI customer summaries (OpenAI — not started)

---

## M4 — CRM App Completion (pending)

### Done

- [x] Company search and filters
- [x] Company profile (contacts, purchases with supplier, product interests)
- [x] Purchase analytics (by customer and product)
- [x] Backend APIs for create/update company and add contact/purchase

### Pending

- [ ] Edit and delete contacts in UI
- [ ] Edit company notes and profile fields in UI
- [ ] Manual merge of duplicate companies
- [ ] Interaction timeline in UI

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
