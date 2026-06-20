# SPIT Student Council — Finance Management Portal

A production-ready **Flask + SQLAlchemy** finance management portal for a college
student council. It manages the complete financial workflow of events — budgets,
advances, reimbursements, vendor payments, prize-pool disbursements, document
management, audit trails, notifications, and reporting — behind a premium
glassmorphism dark-mode UI with motion graphics and cursor interactivity.

---

## Highlights

- **4-role RBAC** — Committee · Finance Secretary · Associate Dean · Dean
- **Multi-level approval workflow** — `Committee → Finance Secretary → Associate Dean → Dean`,
  applied uniformly to Budgets, Advances, Vendor Payments, Reimbursements and Prize Pools
- **Automatic PDF generation** (ReportLab) — Vendor Payment Form, Reimbursement Form,
  Prize Pool Form, and Income & Expenditure Report — generated from user data, no manual work
- **Complete audit trail** — every create / edit / delete / submit / approve / reject is logged
- **Notifications** — approvers are alerted on submission; committee is alerted on approval/rejection
- **Reporting** — per-event Income vs Expenditure, committee-wise roll-up, live dashboard charts
- **Document repository** — upload and categorise bills, invoices, receipts, supporting docs
- **PostgreSQL-ready** — SQLite for development, PostgreSQL in production via a single env var
- **Premium UI** — glassmorphism, aurora background, glow cursor, card tilt, scroll reveals,
  animated count-ups, Chart.js analytics; fully responsive and `prefers-reduced-motion` aware

---

## Tech Stack

| Layer        | Technology                                            |
|--------------|-------------------------------------------------------|
| Backend      | Python, Flask, Flask-Login, Flask-WTF                 |
| ORM          | SQLAlchemy (Flask-SQLAlchemy)                         |
| Database     | SQLite (dev) · PostgreSQL-ready (prod)               |
| Templates    | Jinja2                                                |
| Styling      | Bootstrap-style custom CSS, glassmorphism, Fira Sans / Fira Code |
| PDF          | ReportLab                                             |
| Charts       | Chart.js                                              |

---

## Quick Start

```bash
# 1. Clone and enter the project
cd spit-finance-portal

# 2. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Seed the database with demo data (creates the SQLite DB + 4 role accounts)
python seed.py

# 4. Run the development server
python app.py
#   → http://127.0.0.1:5000
```

> If port 5000 is busy: `PORT=5050 python app.py`

### Demo accounts (each has its own password)

| Role               | Email                  | Password           |
|--------------------|------------------------|--------------------|
| Committee          | committee@spit.ac.in   | `Committee@SPIT26` |
| Finance Secretary  | finance@spit.ac.in     | `Finance@SPIT26`   |
| Associate Dean     | assocdean@spit.ac.in   | `AssocDean@SPIT26` |
| Dean               | dean@spit.ac.in        | `Dean@SPIT26`      |

> Credentials are intentionally **not** displayed on the login page. Change
> these defaults before any real deployment.

Sign in as **Committee** to create events and requests; sign in as the approver
roles to action items in their inbox.

---

## Switching to PostgreSQL (Production)

No code changes required — just set environment variables:

```bash
export FLASK_CONFIG=production
export SECRET_KEY="a-long-random-secret"
export DATABASE_URL="postgresql+psycopg2://user:password@host:5432/spit_finance"

# Install the driver (uncomment in requirements.txt, or):
pip install psycopg2-binary

# Create tables then (optionally) seed
flask --app app init-db
python seed.py
```

The app normalises `postgres://` URLs to `postgresql://` automatically and uses
connection pre-ping for resilience.

---

## Project Structure

```
spit-finance-portal/
├── app.py                       # Entry point
├── config.py                    # Dev / Production config (SQLite ↔ PostgreSQL)
├── seed.py                      # Demo data loader
├── requirements.txt
└── finance_portal/
    ├── __init__.py              # App factory, filters, error handlers, CLI
    ├── extensions.py            # db, login_manager, csrf
    ├── constants.py             # Roles, statuses, the approval chain
    ├── models.py                # All SQLAlchemy models
    ├── forms.py                 # WTForms
    ├── decorators.py            # role_required / committee_required
    ├── services.py              # Audit logging + notifications
    ├── workflow.py              # Generic multi-level approval engine
    ├── pdf.py                   # ReportLab — 4 official forms
    ├── blueprints/              # auth, dashboard, events, budgets, advances,
    │                            #   vendors, reimbursements, prizes,
    │                            #   documents, reports, notifications
    ├── templates/               # Jinja2 (glassmorphism UI)
    └── static/
        ├── css/app.css          # Theme, glassmorphism, motion
        ├── js/app.js            # Glow cursor, tilt, reveals, dynamic rows
        └── uploads/             # Document repository storage
```

---

## Database Schema (overview)

| Table                  | Purpose                                                        |
|------------------------|----------------------------------------------------------------|
| `users`                | Accounts + role (RBAC)                                          |
| `events`               | Events; financial roll-ups (sanctioned, expenditure, balance)  |
| `budgets` / `budget_items`            | Budget header + dynamic line items (qty × unit cost) |
| `advances`             | Advance requests + settlement tracking                         |
| `vendor_payments` / `vendor_payment_items` | Vendor payment + entries + bank details      |
| `reimbursements` / `reimbursement_items`   | Reimbursement + entries + bank details       |
| `prize_pools` / `prize_winners`            | Prize pool + winners + payment tracking      |
| `documents`            | Uploaded bills / invoices / receipts / supporting docs         |
| `audit_logs`           | Polymorphic audit trail across all request types               |
| `notifications`        | Per-user notifications with deep links                         |

Every request table shares a `status` column driven by the same approval engine:
`draft → pending_finance → pending_assoc → pending_dean → approved` (or `rejected`).

---

## The Approval Workflow

```
Committee  ──submit──▶  Finance Secretary  ──approve──▶  Associate Dean  ──approve──▶  Dean  ──approve──▶  APPROVED
                              │                                │                          │
                              └──────────────── reject ────────┴──────────── reject ──────┘──▶  REJECTED
```

- A **Committee** member creates a draft, adds line items, and submits.
- Each approver tier sees only the requests awaiting *their* stage in their inbox.
- Approving advances to the next tier; the Dean's approval finalises it.
- A rejection (with reason) terminates the chain and notifies the creator.
- The engine validates the actor's role **server-side** on every action
  (defense-in-depth, beyond the UI only showing actions to the right tier).

---

## Generated PDF Forms

Each is produced automatically from stored data and opens in the browser:

| Form                        | Route                                   |
|-----------------------------|-----------------------------------------|
| Vendor Payment Form         | `/vendor-payments/<id>/pdf`             |
| Reimbursement Form          | `/reimbursements/<id>/pdf`              |
| Prize Pool Form             | `/prize-pools/<id>/pdf`                 |
| Income & Expenditure Report | `/reports/event/<id>/pdf`               |

---

## Notes

- CSRF protection is enabled on all state-changing forms (Flask-WTF).
- Passwords are hashed with Werkzeug; never stored in plaintext.
- File uploads are size-limited (16 MB) and extension-restricted.
- The UI respects `prefers-reduced-motion` and is responsive down to 375px.

Built for the SPIT Student Council. © 2026.
