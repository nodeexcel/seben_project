# Database Schema — Seben CRM

## Entity Relationship Diagram

```
companies ─────┬──── contacts
               ├──── purchases ──── products
               ├──── product_interests ──── products
               ├──── interactions
               └──── (linked via purchases/interactions) documents
```

## CRM Field Mapping

Fields required by the client spec and where they are stored:

| CRM Field | Database Location | Source |
|---|---|---|
| Company name | `companies.name` | Invoice, contacts, email, WhatsApp title |
| Contact person(s) | `contacts.name` | All sources |
| Email address(es) | `contacts.email` | Contacts, email, invoice |
| Phone number(s) | `contacts.phone` | Contacts, WhatsApp, invoice |
| Country | `companies.country` | Manual, contacts, invoice |
| Product interests | `product_interests` | WhatsApp, email (M3) |
| Product category (Fresh/Frozen) | `companies.product_category`, `products.category` | Product catalog, manual |
| Purchase history | `purchases` | Invoices |
| Quantities purchased | `purchases.quantity` | Invoices |
| Revenue generated | `purchases.revenue` | Invoices |
| First interaction date | `companies.first_interaction_date` | Computed from all sources |
| Last interaction date | `companies.last_interaction_date` | Computed from all sources |
| AI-generated notes | `companies.ai_summary` | OpenAI API |
| Manual notes | `companies.notes` | User input |

---

## Tables

### companies

Central customer/company profile.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | VARCHAR(255) | Required, indexed |
| country | VARCHAR(100) | Optional |
| product_category | ENUM | Fresh, Frozen, Unknown |
| first_interaction_date | DATE | Earliest known interaction |
| last_interaction_date | DATE | Most recent interaction |
| ai_summary | TEXT | AI-generated profile summary |
| notes | TEXT | Manual user notes |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

### contacts

People associated with companies.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| company_id | INTEGER FK → companies | Nullable (unlinked contacts) |
| name | VARCHAR(255) | Required, indexed |
| email | VARCHAR(255) | Normalized lowercase, indexed |
| phone | VARCHAR(50) | E.164 normalized, indexed |
| created_at | TIMESTAMP | |

### products

Product catalog.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | VARCHAR(255) | Unique, indexed |
| category | ENUM | Fresh, Frozen, Unknown |
| created_at | TIMESTAMP | |

### purchases

Purchase/transaction records from invoices.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| company_id | INTEGER FK → companies | Required |
| product_id | INTEGER FK → products | Optional (linked catalog item) |
| product_name_raw | VARCHAR(255) | As extracted from invoice |
| quantity | FLOAT | |
| revenue | FLOAT | |
| currency | VARCHAR(10) | Default USD |
| purchase_date | DATE | Indexed |
| document_id | INTEGER FK → documents | Source invoice |
| created_at | TIMESTAMP | |

### product_interests

Products mentioned or discussed (not yet purchased).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| company_id | INTEGER FK → companies | |
| product_id | INTEGER FK → products | Optional |
| product_name_raw | VARCHAR(255) | As mentioned in comms |
| source | VARCHAR(50) | whatsapp, email |
| mentioned_at | DATE | |
| created_at | TIMESTAMP | |

### interactions

Communication records (WhatsApp, email, manual).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| company_id | INTEGER FK → companies | |
| interaction_type | ENUM | whatsapp, email, manual |
| subject | VARCHAR(500) | Email subject or chat context |
| content | TEXT | Message body |
| interaction_date | TIMESTAMP | Indexed |
| sender | VARCHAR(255) | |
| recipient | VARCHAR(255) | |
| document_id | INTEGER FK → documents | Source file |
| created_at | TIMESTAMP | |

### documents

Tracks every uploaded/processed file.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| source_type | ENUM | whatsapp, email, contact, invoice, manual |
| filename | VARCHAR(500) | Original filename |
| filepath | VARCHAR(1000) | Storage path |
| status | VARCHAR(50) | pending, processing, completed, failed |
| extracted_data | TEXT | JSON extraction result |
| error_message | TEXT | If processing failed |
| processed_at | TIMESTAMP | |
| created_at | TIMESTAMP | |

---

## Enums

### ProductCategory
- `Fresh`
- `Frozen`
- `Unknown`

### DocumentSourceType
- `whatsapp`
- `email`
- `contact`
- `invoice`
- `manual`

### InteractionType
- `whatsapp`
- `email`
- `manual`

---

## Indexes

Key indexes for search performance:

- `companies.name` — company search
- `contacts.name`, `contacts.email`, `contacts.phone` — contact search & linking
- `purchases.purchase_date`, `purchases.company_id` — analytics date ranges
- `purchases.product_name_raw` — product filter
- `interactions.interaction_date` — timeline queries

---

## Linking Rules (v1)

When a file is imported with persist mode:

1. If extracted data has a company name → find existing company (fuzzy ≥85%) or create new
2. For each contact → match by email/phone or create new, link to company
3. For each purchase → create purchase record linked to company
4. For each message → create interaction record linked to company
5. Update `first_interaction_date` / `last_interaction_date` on company

Manual merge UI (Milestone 4) will allow users to combine duplicate profiles.

---

## Pending Client Confirmation

The following fields are in the schema but should be confirmed with the client:

- Is `product_category` at company level or per-product only?
- Default currency for revenue?
- Any additional fields beyond the spec?
- Primary matching key preference (phone vs email vs company name)?
