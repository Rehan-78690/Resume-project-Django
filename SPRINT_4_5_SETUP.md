# Sprint 4 & 5 Backend Implementation - Setup Guide

## Environment Variables Required

Add these to your `.env` file:

```bash
# OpenAI (Required for AI endpoints)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo
OPENAI_MAX_RETRIES=3
OPENAI_TIMEOUT=30

# PDF Providers (Optional - at least one recommended for production)
PDFSHIFT_API_KEY=your-pdfshift-key-here
# OR
CLOUDCONVERT_API_KEY=your-cloudconvert-key-here

# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (optional - defaults to SQLite)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

## Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
./venv/bin/python manage.py migrate
```

### 3. Create Superuser (for admin access)
```bash
./venv/bin/python manage.py createsuperuser
```

### 4. Run Development Server
```bash
./venv/bin/python manage.py runserver
```

### 5. Access the Application

- **API Swagger Docs**: http://localhost:8000/api/docs/
- **Django Admin**: http://localhost:8000/admin/
- **ReDoc**: http://localhost:8000/api/redoc/

## New Endpoints Summary

### Sprint 4 - AI Writing APIs
- `POST /api/ai/summary/` - Generate resume summary
- `POST /api/ai/bullets/` - Generate bullet points
- `POST /api/ai/experience/` - Generate experience description
- `POST /api/ai/cover-letter/base/` - Generate cover letter body
- `POST /api/ai/cover-letter/full/` - Generate full cover letter

### Sprint 4 - PDF Generation
- `GET /api/resumes/{id}/pdf/` - Download resume as PDF

### Sprint 4 - Autosave
- `POST /api/resumes/{id}/autosave/` - Dedicated autosave endpoint

### Sprint 5 - Cover Letters
- `GET /api/cover-letters/` - List cover letters
- `POST /api/cover-letters/` - Create cover letter
- `GET /api/cover-letters/{id}/` - Get cover letter
- `PATCH /api/cover-letters/{id}/` - Update cover letter
- `DELETE /api/cover-letters/{id}/` - Soft delete cover letter
- `POST /api/cover-letters/{id}/duplicate/` - Duplicate cover letter
- `POST /api/cover-letters/{id}/share/` - Create share link
- `DELETE /api/cover-letters/{id}/share/` - Revoke share link

### Sprint 5 - Public Share Links
- `POST /api/resumes/{id}/share/` - Create/get share link for resume
- `DELETE /api/resumes/{id}/share/` - Revoke share link for resume
- `GET /api/public/r/{token}/` - Public resume view (no auth)
- `GET /api/public/c/{token}/` - Public cover letter view (no auth)

### Sprint 5 - Admin APIs (Staff Only)
- `GET /api/admin/users/` - List all users
- `GET /api/admin/users/{id}/` - User details
- `PATCH /api/admin/users/{id}/` - Update user
- `POST /api/admin/users/{id}/toggle_active/` - Block/unblock user
- `GET /api/admin/templates/` - List all templates
- `PATCH /api/admin/templates/{id}/` - Update template
- `POST /api/admin/templates/{id}/toggle_active/` - Activate/deactivate template
- `GET /api/admin/ai-logs/` - View AI usage logs (with filters)

## Rate Limits

Configured in `settings.py`:
- `ai_generation`: 10 requests/hour (heavy operations)
- `ai_rewrite`: 30 requests/hour (lighter operations)
- `user`: 100 requests/hour (general)

## Testing

Run tests:
```bash
./venv/bin/python manage.py test cover_letters
./venv/bin/python manage.py test resumes
./venv/bin/python manage.py test ai_core
```

## Database Models Added

1. **AIUsageLog** (`ai_core` app)
   - Tracks all AI API usage
   - Includes tokens, cost estimates, success/failure

2. **CoverLetter** (`cover_letters` app)
   - Full CRUD for cover letters
   - Can be linked to resumes
   - Soft delete support

3. **ShareLink** (`resumes` app)
   - Generic sharing for resumes and cover letters
   - Token-based public access
   - Revocation and expiry support

## Security Notes

- All admin endpoints require `is_staff=True`
- Share tokens are 32+ bytes urlsafe (unguessable)
- Public endpoints return 404 for invalid/revoked tokens
- AI endpoints have rate limiting
- All AI calls are logged for audit

## Production Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Configure PDF provider (PDFShift or CloudConvert)
- [ ] Set up proper database (PostgreSQL recommended)
- [ ] Configure email backend for notifications
- [ ] Set up static/media file serving
- [ ] Configure CORS for frontend domain
- [ ] Review and adjust rate limits
- [ ] Set up monitoring for AI usage/costs
- [ ] Enable HTTPS
- [ ] Set strong `SECRET_KEY`

## Notes

- PDF generation returns mock PDFs in DEBUG mode without provider keys
- AI logging happens automatically on all AI endpoints
- Soft delete is used consistently across resumes and cover letters
- Existing endpoints remain unchanged - all new features are additive
