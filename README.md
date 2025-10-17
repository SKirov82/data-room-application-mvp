# Acme Dataroom MVP

A professional data room application built with **React + TypeScript + Tailwind + Shadcn/ui** and **Flask + Python + PostgreSQL/SQLite**. Features include nested folders, PDF uploads, search, pagination, and a modern UI with modal dialogs.

## Architecture Overview

- **Backend (`backend/`)**
  - Flask application exposing REST endpoints for folder and file CRUD operations.
  - SQLAlchemy models backed by SQLite for metadata persistence.
  - Uploaded files are stored on disk in `backend/storage` using UUID file names.
  - Automatic creation of a non-deletable root folder ensures there is always an anchor for the hierarchy.

- **Frontend (`frontend/`)**
  - React + TypeScript single page application with Vite bundler.
  - Shadcn/ui components for professional modals, inputs, and buttons.
  - Tailwind CSS for responsive, mobile-friendly styling.
  - Search bar with live results for folders and files.
  - Pagination UI for large folders (50 items per page).

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
pip install -r requirements.txt
FLASK_APP=app.main:app FLASK_RUN_PORT=8000 flask run --debug
```

The API will be available at `http://localhost:8000`. The server creates a SQLite database file in `backend/dataroom.db` and stores file binaries in `backend/storage/`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The SPA runs on `http://localhost:5173` by default and expects the backend at `http://localhost:8000`. You can override the API base URL by creating a `.env` file in `frontend/` with `VITE_API_BASE_URL="http://your-backend"`.

## Usage

1. Launch both the backend and frontend as described above.
2. Visit the frontend URL and **register** a new account or **login** with existing credentials.
3. Once authenticated, the app loads the root data room folder automatically.
4. Use the **New Folder** button to create nested folders.
5. Click **Upload PDF** to upload a PDF into the current folder.
6. Click folder cards to navigate deeper. Breadcrumbs help you move back up the tree.
7. Use the contextual **Rename** and **Delete** actions to manage folders and files.
8. Click **Logout** in the header to sign out.

### Load Mock Data

Populate the database with a sample hierarchy and PDF placeholders to explore the UI quickly:

```bash
cd backend
python -m app.mock_data
```

The command is idempotent—it can be run multiple times without creating duplicate records.

## Key Features

### ✨ Core Functionality
- **Nested Folders**: Create unlimited folder hierarchies
- **PDF Upload**: 100MB file size limit with validation
- **Rename & Delete**: Full CRUD on folders and files
- **Cascade Delete**: Deleting folders removes all children

### 🎨 UX Enhancements  
- **Shadcn/ui Modals**: Professional dialogs replace browser prompts
- **Breadcrumb Navigation**: Always know your location
- **Pagination**: Handle thousands of files (50 per page)
- **Search**: Real-time folder and file search

### 🔒 Security & Authentication
- **User Authentication**: Session-based login/register with secure password hashing
- **Protected Routes**: All dataroom features require authentication
- **PostgreSQL Support**: Production-ready database
- **File Size Limits**: 100MB max upload
- **CORS Protection**: Restricted origins with credentials support
- **UUID File Storage**: Prevents filename collisions

## Design Notes

- **UUID File Storage**: Prevents filename collisions, easy migration to S3
- **Cascade Delete**: Recursive removal with disk cleanup
- **Optimistic UI**: Immediate feedback, refresh on confirm
- **Type Safety**: Full TypeScript coverage in frontend
- **Indexed Queries**: Fast lookups for large datasets

## Testing

Run backend unit tests:

```bash
cd backend
pytest
```

Run frontend tests:

```bash
cd frontend
npm test
```

## Production Deployment

The application supports PostgreSQL for production use:

1. Set `DATABASE_URL` environment variable in `backend/.env`
2. Set `SECRET_KEY` for session security (required for auth)
3. Configure `VITE_API_BASE_URL` in frontend

Example `.env`:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/dataroom
SECRET_KEY=your-secret-key-generate-with-secrets-module
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## API Endpoints

- `GET /folders/root` - Get root folder
- `GET /folders/{id}/contents?page=1&page_size=50` - List folder contents (paginated)
- `POST /folders` - Create folder
- `PATCH /folders/{id}` - Rename folder
- `DELETE /folders/{id}` - Delete folder (cascade)
- `POST /files?folder_id={id}` - Upload PDF
- `GET /files/{id}/download` - Download file
- `PATCH /files/{id}` - Rename file
- `DELETE /files/{id}` - Delete file
- `GET /search?q={query}` - Search folders and files
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/logout` - Logout user
- `GET /auth/me` - Get current user

## Tech Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Shadcn/ui, Radix UI, Lucide Icons

**Backend:** Flask 3.0, SQLAlchemy 2.0, Pydantic, Flask-CORS

**Database:** SQLite (dev), PostgreSQL (prod)

**Testing:** Pytest (backend), Vitest (frontend)
