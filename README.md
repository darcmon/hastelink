# Hastelink

Hastelink is a versioned file-publishing app for stable, human-readable links. Administrators create a location such as `/employee-handbook`, upload a replacement file, and approve it before it becomes public. The URL stays the same while the file behind it changes.

## What it does

- Creates named file locations with stable public slugs
- Stores uploaded files in S3-compatible object storage
- Tracks pending, approved, rejected, and superseded versions
- Keeps the currently approved file live until a replacement is approved
- Provides an admin approval queue and location management UI
- Supports email/password API login plus Microsoft and Google OAuth
- Records uploads, reviews, and public file access in an audit log
- Streams approved files inline from `GET /{slug}`

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL
- **Frontend:** Vue 3, TypeScript, Vue Router, Vite
- **Storage:** MinIO locally; AWS S3, Cloudflare R2, or another S3-compatible service in production
- **Authentication:** JWT bearer tokens, Microsoft OAuth, and Google OAuth
- **Local infrastructure:** Docker Compose

## Local development

Local development data is disposable. Database migrations, resets, and test setup
may delete or recreate it. This policy does not apply to production data.

### Prerequisites

- Python 3.11 or newer
- Node.js and npm
- Docker with Docker Compose

### 1. Configure the app

Copy the example environment file:

```bash
cp .env.example .env
```

For local development, keep the first PostgreSQL and MinIO values in `.env` and remove or comment out the duplicate production S3/R2 block. At minimum, set secure local admin credentials:

```dotenv
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=choose-a-password
SECRET_KEY=replace-this-with-a-random-secret
```

OAuth credentials are optional unless you want to use the current frontend login screen. See [OAuth setup](#oauth-setup) below.

### 2. Start PostgreSQL and MinIO

```bash
docker compose up -d
```

This starts:

- PostgreSQL at `localhost:5432`
- MinIO's S3 API at `http://localhost:9000`
- The MinIO console at `http://localhost:9001`

Open the MinIO console, sign in with `minioadmin` / `minioadmin`, and create the bucket configured by `S3_BUCKET` (the example uses `file-approval`).

### 3. Start the backend

Create a virtual environment and install the Python package:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn backend.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`. On startup, the backend creates missing tables and seeds the first admin user from `ADMIN_EMAIL` and `ADMIN_PASSWORD` when no admin exists.

### 4. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend uses `http://localhost:8000` by default. To point it elsewhere, set `VITE_API_URL` before starting Vite.

## OAuth setup

The admin UI currently presents Microsoft and Google sign-in. Register OAuth applications with these local callback URLs:

```text
http://localhost:8000/admin/auth/microsoft/callback
http://localhost:8000/admin/auth/google/callback
```

Then configure the corresponding values in `.env`:

```dotenv
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT=common
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FRONTEND_URL=http://localhost:5173
```

OAuth is currently allowlist-based: the provider email must already match an active admin user. The first successful OAuth login binds that user's provider identity. `GOOGLE_SELF_SERVE_ENABLED` should remain `false`; automatic onboarding is not implemented yet.

For direct API use, password login is available at `POST /admin/login` and returns a bearer token.

## Typical workflow

1. Sign in as an administrator.
2. Create a location with a slug and display name.
3. Upload a file to that location through the API.
4. Approve or reject the pending version from the dashboard.
5. Visit `http://localhost:8000/{slug}` to view the approved file.
6. Upload and approve a newer version to replace the public file without changing its URL.

Uploads default to a 50 MB limit and accept PDFs, PNGs, and JPEGs. Configure these with `MAX_UPLOAD_SIZE_MB` and the comma-separated `ALLOWED_FILE_TYPES` value.

## Useful API routes

| Method      | Route                              | Purpose                                   |
| ----------- | ---------------------------------- | ----------------------------------------- |
| `GET`       | `/health`                          | Health check                              |
| `POST`      | `/admin/login`                     | Password login                            |
| `GET`       | `/admin/me`                        | Current admin profile                     |
| `GET/POST`  | `/admin/locations`                 | List or create locations                  |
| `GET/PATCH` | `/admin/locations/{slug}`          | Read or update a location                 |
| `POST`      | `/admin/locations/{slug}/upload`   | Upload a pending version                  |
| `GET`       | `/admin/versions/pending`          | List pending approvals                    |
| `POST`      | `/admin/versions/{id}/approve`     | Approve and publish a version             |
| `POST`      | `/admin/versions/{id}/reject`      | Reject a pending version                  |
| `GET`       | `/admin/locations/{slug}/versions` | Browse a location's version archive       |
| `GET`       | `/admin/versions/{id}/download`    | Download a stored version                 |
| `DELETE`    | `/admin/versions/{id}`             | Soft-delete a non-approved version        |
| `GET`       | `/{slug}`                          | Stream the currently approved public file |

Admin routes require `Authorization: Bearer <token>` except for login and OAuth entry points.

## Project structure

```text
backend/
  main.py          FastAPI app and startup lifecycle
  routers/         Auth, locations, uploads, approvals, archive, and public routes
  models/          SQLAlchemy database models
  services/        File storage, approvals, audit logging, and cache logic
frontend/
  src/views/       Login, dashboard, OAuth callback, and locations screens
  src/api/         Authenticated API client
alembic/           Database migration configuration and revisions
docker-compose.yml Local PostgreSQL and MinIO services
```

## Production notes

- Replace all example credentials and use a strong `SECRET_KEY`.
- Set `ALLOWED_ORIGINS` and `FRONTEND_URL` to the deployed frontend URL.
- Configure one S3-compatible storage block only. For Cloudflare R2, use the account endpoint and set `AWS_REGION=auto`.
- Create the configured bucket before uploading files.
- Keep Google self-service disabled until tenant isolation and onboarding are implemented.
- Run the frontend production build with `npm run build` from `frontend/`.
