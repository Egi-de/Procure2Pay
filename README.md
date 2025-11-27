# Procure2Pay

## Project Overview

Procure2Pay is a comprehensive procure-to-pay (P2P) platform designed to streamline the procurement lifecycle within organizations. Inspired by industry-leading solutions like Payhawk, this application facilitates end-to-end management of purchase requests, from submission by staff to multi-level approvals, automated purchase order (PO) generation, and receipt validation. The platform ensures compliance, efficiency, and transparency in procurement processes by leveraging role-based workflows, document automation, and secure authentication.

### Key Business Value

- **Efficiency**: Automates manual approvals and document handling, reducing processing time from days to minutes.
- **Compliance**: Enforces multi-level approvals with audit trails and optimistic locking to prevent conflicts.
- **Accuracy**: Uses OCR and metadata extraction to validate receipts against POs, minimizing errors in financial reconciliation.
- **Scalability**: Built with modern full-stack technologies, supporting deployment from local development to cloud platforms like Render.
- **User-Centric**: Role-specific dashboards provide intuitive interfaces for staff, approvers, and finance teams.

The workflow is as follows:

1. **Staff** submits a purchase request with line items and a vendor proforma (PDF/image).
2. **Approver L1** reviews and approves/rejects the request.
3. **Approver L2** (if required based on amount thresholds) performs secondary approval.
4. **Finance** monitors all requests and validates receipts post-PO generation.
5. Upon final approval, a PO is automatically generated and stored.
6. Staff uploads receipts, which are validated against the PO for discrepancies (e.g., amount, vendor).

This platform is production-ready and deployed at [https://procure2pay.onrender.com/](https://procure2pay.onrender.com/).

### Screenshots

To visualize the application, refer to the following screenshots (images should be placed in `docs/images/` for local viewing):

- ![Login Page](docs/images/login.png)  
  _The secure login interface for all users._

- ![My Requests - Staff View](docs/images/my-requests-staff.png)  
  _Staff dashboard showing personal requests with status tracking (e.g., approved car purchase)._

- ![Approval Queue - Approver View](docs/images/approval-queue-approver.png)  
  _Approver L1/L2 queue for pending requests, with actions to approve/reject._

- ![Approval Queue - Finance View](docs/images/approval-queue-finance.png)  
  _Finance overview of all requests in the system, including pending and historical data._

- ![Django Admin Interface](docs/images/django-admin.png)  
  _Administrative panel for managing users, groups, and authentication._

## Tech Stack

Procure2Pay is a full-stack application built with robust, industry-standard technologies:

- **Backend**: Django 5.x + Django REST Framework (DRF) for APIs, Celery (if async tasks are enabled), and custom apps for user management and workflows.
- **Database**: PostgreSQL 15 (production/recommended) or SQLite (local development).
- **Frontend**: React 19 + Vite for fast builds, Tailwind CSS for styling, React Router for navigation, and Axios for API calls.
- **Authentication**: JWT (via djangorestframework-simplejwt) with role-based access control (RBAC) using custom user groups.
- **Document Processing**: PyPDF2 and pdfplumber for PDF parsing, Pillow for image handling, pytesseract for OCR on receipts/proformas.
- **Containerization & Orchestration**: Docker for services, docker-compose for local development, Nginx for serving static React assets.
- **Additional Libraries**:
  - Backend: drf-yasg for Swagger API docs, django-cors-headers for frontend integration, Pillow/tesseract for media processing.
  - Frontend: React Context API for state management (Auth, Notifications, Theme), React Toastify for notifications.
- **DevOps**: GitHub Actions for CI/CD (linting, testing, Docker builds), Render for cloud deployment.

### Architecture

The application follows a client-server architecture:

- **Server**: Handles API endpoints, business logic, database interactions, and file storage (media/proformas, purchase_orders, receipts).
- **Client**: Single-page application (SPA) with role-aware routing and components (e.g., forms, modals, lists).
- **Communication**: RESTful APIs over HTTPS, with JWT tokens for session management.

A simple text-based architecture diagram:

```
[React Frontend (Vite/Nginx)] <--> [Django API (Gunicorn)] <--> [PostgreSQL DB]
                          |                  |
                    [File Uploads]    [Document Services (OCR/PDF)]
                          |                  |
                    [Media Storage]   [Workflow Engine (Approvals)]
```

## Features

### User Roles and Permissions

The platform defines four primary roles, each with tailored access:

- **STAFF**: Submit and track personal requests; upload receipts for owned POs.
- **APPROVER_L1**: Review and approve/reject low-value requests (< threshold, configurable).
- **APPROVER_L2**: Handle high-value requests escalated from L1.
- **FINANCE**: View all requests, monitor workflows, and access validation reports.
- **Superuser (Admin)**: Full access via Django admin for user/group management.

Permissions are enforced via Django's group-based system and DRF's permission classes.

### Core Features

- **Purchase Request Management**:
  - Create requests with multiple line items (title, amount, description).
  - Upload proforma documents (PDF/images) for metadata extraction (vendor, total amount, currency).
  - Real-time status updates (Pending, Approved L1, Approved L2, Rejected, PO Generated).
- **Approval Workflow**:
  - Multi-level routing based on amount (e.g., < $1,000 → L1 only; > $1,000 → L1 + L2).
  - Optimistic locking to handle concurrent approvals.
  - Audit trail logging all actions (who, when, comments).
  - Email notifications for rejections/approvals (via Django's email backend).
- **Purchase Order Automation**:
  - Auto-generate PO upon final approval, including metadata and a downloadable text/PDF artifact.
  - Stored in `media/purchase_orders/` with unique filenames (e.g., PO-YYYYMMDD-hash.pdf).
- **Receipt Validation**:
  - Staff uploads receipts post-PO.
  - OCR extracts amount/vendor/date; compares against PO (tolerances for minor discrepancies).
  - Generates validation report (match/mismatch) with highlighted issues.
- **Dashboards and UI**:
  - Role-specific views: "My Requests" for staff, "Approval Queue" for approvers/finance.
  - Responsive design with pagination, search, and toast notifications.
  - Unauthorized access redirects to a custom 403 page.
- **API Documentation**: Interactive Swagger UI at `/api/docs/` and ReDoc at `/api/redoc/`.
- **Security**: Rate throttling (via DRF throttles), CSRF protection, secure file uploads (validated extensions/sizes).

### Django Apps Breakdown

- **home**: Custom User model (with roles), authentication views/serializers (e.g., `/api/me/` for profile), admin configurations.
- **requests_app**: Core logic including models (Request, Approval, LineItem, PurchaseOrder, Receipt), views (CRUD for requests/approvals), serializers (nested for items/files), services (document_processing.py for extraction/generation/validation), notifications (email templates), and permissions/throttles.

## Production Access

The application is deployed on Render at **https://procure2pay.onrender.com/**.

### Demo Credentials

**⚠️ Warning**: These credentials are for demonstration/testing purposes only. Do not use in production without changing passwords and enabling additional security (e.g., 2FA, IP whitelisting). Change them immediately upon access.

- **Staff** (for submitting requests):  
  Username: `egide`  
  Password: `test@123`

- **Approver L1**:  
  Username: `ishimwe-paccy`  
  Password: `@alma2025`

- **Approver L2**:  
  Username: `cedrick-izabayo`  
  Password: `acedo@123`

- **Finance** (for monitoring):  
  Username: `sonia`  
  Password: `egide123`

- **Django Superuser/Admin** (for backend management, access at `/admin/`):  
  Username: `egide`  
  Password: `test@123`

To log in:

1. Navigate to the production URL.
2. Enter credentials on the login page.
3. Use role-specific dashboards to interact (e.g., create a request as staff, approve as L1).

For admin access: Append `/admin/` to the URL and log in with superuser credentials.

## Local Development

### Prerequisites

- Python 3.10+ (for backend).
- Node.js 18+ and npm (for frontend).
- Docker and docker-compose (for containerized setup).
- Git for cloning the repository.

### Backend Setup

1. Navigate to the server directory:
   ```bash
   cd server
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows (CMD): venv\Scripts\activate
   # On Windows (PowerShell): venv\Scripts\Activate.ps1
   # On macOS/Linux: source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy and configure environment:
   ```bash
   copy env.sample .env  # Windows
   # Or: cp env.sample .env (macOS/Linux)
   ```
   Edit `.env`:
   - Set `DJANGO_SECRET_KEY` (generate via Django docs).
   - Configure `DATABASE_URL` (e.g., `sqlite:///db.sqlite3` for local or PostgreSQL creds).
   - Add `ALLOWED_HOSTS=*` for dev, `CORS_ALLOWED_ORIGINS=http://localhost:4173` for frontend.
   - Set JWT settings (e.g., `SIMPLE_JWT_EXPIRATION`).
5. Run migrations and create superuser:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser  # Use demo creds or new ones
   ```
6. Collect static files (if needed):
   ```bash
   python manage.py collectstatic --noinput
   ```
7. Start the development server:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   Access backend at `http://localhost:8000/admin/` or API at `http://localhost:8000/api/docs/`.

**Troubleshooting Backend**:

- **DB Connection Error**: Ensure PostgreSQL is running (via Docker) or switch to SQLite in `.env`.
- **CORS Issues**: Verify `CORS_ALLOWED_ORIGINS` includes frontend URL.
- **File Uploads**: Set `MEDIA_URL=/media/` and serve media in dev via `runserver`.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd client/procure2pay
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Configure environment: Set `VITE_API_BASE_URL=http://localhost:8000` in a `.env` file (or via Vite config).
4. Start the development server:
   ```bash
   npm run dev -- --host
   ```
   Access frontend at `http://localhost:4173` (Vite default).

**Troubleshooting Frontend**:

- **API Calls Fail**: Check browser console for CORS/network errors; ensure backend is running.
- **Build Issues**: Run `npm run build` to verify; check Tailwind/PostCSS configs.
- **Hot Reload**: If not working, restart with `--host 0.0.0.0`.

### Database Configuration

- **Local (SQLite)**: No extra setup; uses `db.sqlite3` in server/.
- **Production-like (PostgreSQL)**: Run via Docker (see below) or install locally. Update `DATABASES` in `settings.py` or `.env`.

## Dockerized Stack

For a full local environment mirroring production:

1. Ensure Docker and docker-compose are installed.
2. Copy and update `.env` in root (shared with compose):
   - Include all backend env vars (DB creds, secrets).
   - Set `VITE_API_BASE_URL=http://localhost:8000` for frontend.
3. Build and run:
   ```bash
   docker-compose up --build
   ```
   - `--build` rebuilds images on changes.
   - Use `-d` for detached mode.

### Services

- **backend**: Django + Gunicorn on port 8000. Runs migrations on startup.
- **frontend**: React build served by Nginx on port 4173 (static files from `/dist`).
- **db**: PostgreSQL 15 with volume `./postgres_data` for persistence.
- **(Optional) redis/celery**: If async tasks (e.g., email) are enabled, add services.

Access:

- Frontend: `http://localhost:4173`
- Backend API: `http://localhost:8000/api/docs/`
- Admin: `http://localhost:8000/admin/`
- DB: Connect via `psql` to `localhost:5432` (user/password from `.env`).

**Stopping/Resetting**:

- `docker-compose down` to stop.
- `docker-compose down -v` to remove volumes (resets DB).
- Logs: `docker-compose logs -f backend` for debugging.

**Troubleshooting Docker**:

- **Port Conflicts**: Change ports in `docker-compose.yml` (e.g., 8001 for backend).
- **Build Fails**: Ensure Node/Python versions match Dockerfiles; clear cache with `--no-cache`.
- **Media Files**: Volumes map `./server/media` for persistence.

## API Reference

All APIs are prefixed with `/api/` and require JWT authentication (except login). Use `/api/docs/` for interactive testing.

### Authentication Endpoints

| Endpoint              | Method | Role | Description                         | Request Example                                   | Response Example                                    |
| --------------------- | ------ | ---- | ----------------------------------- | ------------------------------------------------- | --------------------------------------------------- |
| `/api/token/`         | POST   | Any  | Login and get access/refresh tokens | `{ "username": "egide", "password": "test@123" }` | `{ "access": "jwt...", "refresh": "jwt..." }`       |
| `/api/token/refresh/` | POST   | Auth | Refresh access token                | `{ "refresh": "jwt..." }`                         | `{ "access": "new-jwt..." }`                        |
| `/api/me/`            | GET    | Auth | Get current user profile            | -                                                 | `{ "id": 1, "username": "egide", "role": "STAFF" }` |

### Request Management Endpoints

| Endpoint                             | Method | Role          | Description                                                | Notes                                    |
| ------------------------------------ | ------ | ------------- | ---------------------------------------------------------- | ---------------------------------------- |
| `/api/requests/`                     | POST   | STAFF         | Create new request (multipart: items JSON + proforma file) | Items: `[{title: "Car", amount: 50000}]` |
| `/api/requests/`                     | GET    | Auth          | List requests (filtered by role: own/pending/all)          | Query params: `?status=pending&limit=10` |
| `/api/requests/{id}/`                | GET    | Auth          | Retrieve single request details                            | Includes line items, approvals, files    |
| `/api/requests/{id}/update/`         | PATCH  | STAFF (owner) | Update request (before approval)                           | Partial updates (e.g., add comments)     |
| `/api/requests/{id}/approve/`        | PATCH  | APPROVER      | Approve at current level                                   | Body: `{ "comments": "Approved" }`       |
| `/api/requests/{id}/reject/`         | PATCH  | APPROVER      | Reject with reason                                         | Body: `{ "reason": "Budget exceeded" }`  |
| `/api/requests/{id}/submit-receipt/` | POST   | STAFF (owner) | Upload receipt for PO validation                           | Multipart: receipt file                  |

### Additional Endpoints

- `/api/notifications/`: GET/POST for user alerts (e.g., approval pings).
- `/api/purchase-orders/{id}/`: GET for PO download/view.
- `/api/receipts/{id}/validate/`: POST to trigger validation (auto on upload).

**Error Handling**: Standard DRF responses (400/401/403/404/500) with detail messages. Throttling: 100 requests/hour per user.

**Testing APIs**: Use Swagger or tools like Postman. Export collection from `/api/docs/`.

## Document Processing Details

The `requests_app/services/document_processing.py` handles all file operations securely.

### Proforma Extraction

- **Input**: PDF or image upload.
- **Process**: Parse with pdfplumber/PyPDF2 for text; fallback to pytesseract OCR for scanned docs.
- **Output**: Metadata dict `{ "vendor": "ABC Corp", "total_amount": 50000.0, "currency": "USD" }`.
- **Supported Formats**: PDF, JPEG, PNG. Validates numeric amounts/currencies.
- **Limitations**: OCR accuracy ~90% for clear scans; handles multi-page but assumes totals on last page.

### PO Generation

- **Trigger**: Final approval.
- **Process**: Compile request data into structured text/PDF (using ReportLab if extended); sign digitally (hash-based).
- **Output**: File saved to `media/purchase_orders/PO-YYYYMMDD-hash.pdf/txt`; metadata in DB.
- **Example**: Includes line items, approver signatures, totals.

### Receipt Validation

- **Input**: Uploaded receipt file post-PO.
- **Process**:
  1. Extract metadata (amount, vendor, date) via OCR/PDF parsing.
  2. Compare against PO: Check thresholds (e.g., amount ±5%, vendor match).
  3. Generate report: `{ "match": true, "discrepancies": ["Amount: $50,000 vs $49,500"], "confidence": 0.95 }`.
- **Output**: Stored in DB; UI shows modal with results (e.g., ReceiptValidationModal.jsx).
- **Edge Cases**: Non-numeric/zero amounts flagged; incomplete docs rejected.

**Extending**: Add support for invoices or integrate with external OCR services (e.g., Google Vision) for better accuracy.

## Testing

### Manual Testing (QA Checklist)

Use production/demo credentials to test end-to-end. Follow these steps:

1. **Login and Role Verification**:

   - Log in as each role; confirm dashboard loads correctly (e.g., staff sees "My Requests", finance sees all).
   - Access unauthorized areas → expect 403 redirect.

2. **Request Creation (as Staff - egide/test@123)**:

   - Navigate to "New Request".
   - Add line items (e.g., title: "Laptop", amount: $1000).
   - Upload a proforma (use sample from `server/media/proformas/` or create PDF).
   - Submit → Verify status "Pending L1" and email notification (if configured).

3. **Approval Workflow (as Approver L1 - ishimwe-paccy/@alma2025)**:

   - View "Approval Queue" → See pending request.
   - Approve → Status updates to "Pending L2" (if > threshold).
   - For low-value: Approve → Triggers L2 skip and PO generation.
   - Reject one → Check rejection reason and staff notification.

4. **Secondary Approval (as Approver L2 - cedrick-izabayo/acedo@123)**:

   - Approve high-value request → PO generated; download/view PO.

5. **Finance Monitoring (as sonia/egide123)**:

   - View full queue → Filter by status/date.
   - Confirm audit trail and no edit access.

6. **Receipt Validation (as Staff)**:

   - After PO, upload receipt (matching/mismatching sample from `server/media/receipts/`).
   - View validation modal → Check match report (e.g., discrepancies highlighted).

7. **Edge Cases**:

   - Concurrent approvals → Verify locking prevents duplicates.
   - Invalid files → Expect upload errors (e.g., non-PDF).
   - Token expiry → Refresh and re-login.

8. **Admin Tasks (Superuser)**:
   - Log in at `/admin/` → Manage users/groups (add new staff, assign roles).

**Expected Outcomes**: All workflows complete without errors; files persist in media folders; logs show actions.

### Automated Testing

- **Backend**: Django TestCase/pytest in `server/requests_app/tests.py`.
  - Run: `cd server && pytest` (install pytest if needed: `pip install pytest`).
  - Coverage: Focus on models (workflow states), views (permissions), services (extraction accuracy).
  - Example: Test request creation, approval transitions, validation with mock files.
- **Frontend**: Jest + React Testing Library.
  - Run: `cd client/procure2pay && npm test`.
  - Test components (e.g., Form.jsx validation), API integrations (mock Axios).
- **End-to-End**: Use Cypress (add via `npm install cypress`); script workflows.
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`) runs tests on push/PR.

**Coverage Goal**: Aim for 80%+; use `coverage run -m pytest` for reports.

## Deployment

### Render-Specific Deployment (Current Production)

The app is deployed on Render using Docker. Steps to replicate/update:

1. **Prepare Repository**:

   - Ensure `Dockerfile` (root/client/server) and `docker-compose.yml` are up-to-date.
   - Set production env: Update `settings.py` for `DEBUG=False`, `ALLOWED_HOSTS=['procure2pay.onrender.com']`, `CORS_ALLOWED_ORIGINS=['https://procure2pay.onrender.com']`.
   - Configure `.env`: Production DB (Render Postgres), `DJANGO_SECRET_KEY`, email SMTP if needed.

2. **Build and Push Images**:

   - Use GitHub Actions (`.github/workflows/docker-image.yml`) to build/push to Render or Docker Hub.
   - Manual: `docker build -t procure2pay-backend .` (in server/), push to registry.

3. **Render Setup**:

   - Create services: Web Service (Docker from GitHub repo), Postgres Database.
   - Env Vars: All from `.env` (e.g., `DATABASE_URL`, `VITE_API_BASE_URL=https://procure2pay.onrender.com`).
   - Build Command: `docker-compose up --build` (or custom script).
   - Start Command: For backend: `gunicorn procure2pay.wsgi:application --bind 0.0.0.0:$PORT`.
   - For frontend: Use static site or Docker with Nginx.

4. **Post-Deploy**:

   - Run migrations: SSH or release command `python manage.py migrate`.
   - Collect static: `python manage.py collectstatic`.
   - Seed data: Create users via admin or fixture.
   - Health Check: `/api/me/` or custom endpoint.

5. **Scaling/Monitoring**:
   - Render auto-scales; add logs via `docker-compose logs`.
   - Metrics: Integrate Sentry for errors, Prometheus for APIs.

### General Deployment to Other Platforms

- **Heroku/Fly.io/Railway**: Similar Docker push + managed DB.
- **AWS/K8s**: Use ECS/EKS with RDS; CI/CD via GitHub Actions.
- **Custom Server**: `docker-compose up -d` on VPS; Nginx reverse proxy for HTTPS.

**Security Notes**: Use HTTPS only; rotate secrets; limit file uploads (e.g., 10MB via `DATA_UPLOAD_MAX_MEMORY_SIZE`); scan deps with `pip-audit`/`npm audit`.

## Troubleshooting & FAQs

- **"CORS Error"**: Add frontend origin to `CORS_ALLOWED_ORIGINS` in settings.py; restart server.
- **"No such table"**: Run `migrate` after DB changes.
- **JWT Invalid**: Check expiry in `.env`; use refresh endpoint.
- **OCR Fails**: Ensure Tesseract installed (`brew install tesseract` on macOS); test with clear images.
- **Slow Builds**: Increase Docker resources; use multi-stage Dockerfiles.
- **Media Not Serving**: In dev, add `+ static/media/` to `runserver`; in prod, configure Nginx/Render storage.
- **Role Not Assigned**: Use Django admin to add users to groups (STAFF, etc.).
- **Deployment Fails on Render**: Check logs for missing env vars; ensure Dockerfile exposes correct port.

For issues, check server logs (`docker logs backend`) or browser console.

## Contributing

1. Fork the repo and create a feature branch (`git checkout -b feature/amazing-feature`).
2. Commit changes (`git commit -m 'Add some amazing feature'`).
3. Push to branch (`git push origin feature/amazing-feature`).
4. Open a Pull Request.

Guidelines:

- Follow PEP 8 (Python) and ESLint (JS).
- Add tests for new features.
- Update README for changes.

## License

MIT License - see LICENSE file (or add one if missing). Free for non-commercial use; contact for enterprise.

---

_Last Updated: November 2024. For support, reach out via GitHub issues._
