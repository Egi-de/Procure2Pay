# Procure2Pay

A mini procure-to-pay platform inspired by Payhawk. Staff can submit purchase requests with vendor proformas, approvers collaborate through multi-level workflows, finance teams monitor approvals, and receipts are validated automatically against the generated purchase orders.

## Tech Stack

- Django 5 + Django REST Framework
- PostgreSQL (docker) or SQLite (local dev)
- React 19 + Vite + Tailwind CSS
- JWT auth (SimpleJWT) with role-based access
- Document processing via PyPDF2, pdfplumber, Pillow, pytesseract
- Docker & docker-compose for local container orchestration

## Features

- Custom user roles (`STAFF`, `APPROVER_L1`, `APPROVER_L2`, `FINANCE`)
- Purchase requests with line items, file uploads, workflow tracking
- Multi-level approvals with optimistic locking and audit trail
- Automatic PO generation after the final approval
- Receipt ingestion + OCR/metadata comparison vs PO with discrepancy report
- React dashboard with role-aware views, approval buttons, receipt upload flow
- Swagger UI available under `/api/docs/`

### Django apps

- `home`: custom `User` model, role management, auth helpers (`/api/me/`)
- `requests`: purchase request workflow, approvals, document automation

## Local Development

### Backend

```bash
cd server
python -m venv venv
venv\Scripts\activate            # .\venv\Scripts\activate on PowerShell
pip install -r requirements.txt
copy env.sample .env             # adjust secrets + DB config
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

### Frontend

```bash
cd client/procure2pay
npm install
npm run dev -- --host
```

Set `VITE_API_BASE_URL=http://localhost:8000` (or your deployed origin) for the SPA to reach the API.

## Dockerized Stack

```bash
docker-compose up --build
```

Services:

- `backend`: Django + Gunicorn exposed on `http://localhost:8000`
- `frontend`: Static React app served via Nginx on `http://localhost:4173`
- `db`: PostgreSQL 15 with persistent volume

Update the compose file/environment to point `VITE_API_BASE_URL` and `ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS` to your production domain before deployment.

## API Reference (excerpt)

| Endpoint                             | Method | Role          | Description                                               |
| ------------------------------------ | ------ | ------------- | --------------------------------------------------------- |
| `/api/token/`                        | POST   | Any           | Obtain JWT pair                                           |
| `/api/token/refresh/`                | POST   | Authenticated | Refresh token                                             |
| `/api/me/`                           | GET    | Authenticated | Current user profile                                      |
| `/api/requests/`                     | POST   | Staff         | Create request (multipart with `items` JSON + `proforma`) |
| `/api/requests/`                     | GET    | Authenticated | List requests (auto-filtered by role)                     |
| `/api/requests/{id}/approve/`        | PATCH  | Approvers     | Approve current level                                     |
| `/api/requests/{id}/reject/`         | PATCH  | Approvers     | Reject                                                    |
| `/api/requests/{id}/submit-receipt/` | POST   | Staff owner   | Upload receipt for validation                             |

More endpoints plus schema are browsable on `/api/docs/` and `/api/redoc/`.

### Document Processing

- `extract_proforma_metadata`: extracts vendor/amount/currency from uploaded PDF/image
- `generate_purchase_order`: builds PO metadata + persists a signed text artifact
- `validate_receipt`: runs OCR / PDF parsing on receipts and compares against PO metadata

### API Documentation

Export Postman collection from Swagger UI at `/api/docs/` for easy testing and integration.

## Deployment

Deployable to any container host (AWS ECS/Fargate, Fly.io, Render, Railway, etc.). Typical steps:

1. Push images built from the provided Dockerfiles to your registry.
2. Provision managed Postgres (or reuse compose spec).
3. Configure environment variables (`DJANGO_SECRET_KEY`, DB creds, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, JWT lifetimes).
4. Run `python manage.py migrate` via release task.
5. Point your domain/DNS + TLS, update `VITE_API_BASE_URL`.

_Update this README with the final production URL once deployed._

## Testing

Manual QA checklist:

- Create requests as staff (with & without proforma)
- Approve/reject at both levels, ensure lock once terminal
- Verify PO file + metadata stored on final approval
- Upload receipts and confirm validation feedback for matching/mismatching docs
- Confirm finance sees all records, staff restricted to their own

Additional automated tests can be added under `server/requests/tests.py` (pytest or Django TestCase) focusing on workflow transitions and permissions.
