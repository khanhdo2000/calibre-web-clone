# Production Deployment Guide

## Overview

The base `docker-compose.yml` is **production-ready by default**. You can deploy directly without any overrides.

## Quick Start

**Deploy in Production Mode:**

```bash
# Option 1: Use base compose file (recommended)
docker-compose up -d --build

# Option 2: Explicitly use production override (optional)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Base Config is Production-Ready

The base `docker-compose.yml` file defaults to production settings:

| Feature | Base (Production) | Dev Override |
|---------|------------------|--------------|
| Frontend | Nginx serving static files | Vite dev server |
| Frontend Port | 80 (internal) | 5173 (internal) |
| Backend Reload | Disabled | Enabled |
| Source Code Mounts | No | Yes (hot reload) |
| Build Required | Yes | No |
| Performance | Faster (static files) | Slower (dev server) |
| Bundle Size | Smaller (optimized) | Larger (dev deps) |
| Library Path | `/opt/calibre-library-read` | `~/dev/calibre-web-data/...` |

## Environment Configuration

### Production .env

Create a `.env` file for production:

```bash
# Production uses defaults from docker-compose.yml
# Only set what differs from defaults

# Server paths
CALIBRE_LIBRARY_PATH=/opt/calibre-library-read

# API URLs
VITE_API_URL=/api  # Or absolute URL if not using nginx proxy
FRONTEND_URL=https://your-domain.com

# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# Security
SECRET_KEY=your-secret-key-min-32-chars

# ... other production settings
```

## Default Production Settings

The base `docker-compose.yml` includes:
- Production `Dockerfile` with multi-stage build (Node → Nginx)
- No source code volume mounts
- Frontend serves pre-built static files via Nginx on port 80
- Backend runs without `--reload` flag
- Library path defaults to `/opt/calibre-library-read`

## Updating Production

When you make code changes and need to deploy:

```bash
# Pull latest code
git pull

# Rebuild and restart (base config is production-ready)
docker-compose up -d --build

# Or rebuild specific service
docker-compose up -d --build frontend
```

## Server Deployment (Coolify, VPS, etc.)

For server deployment:

### Default Deployment (Recommended)

Simply deploy the base `docker-compose.yml`:
```bash
# On your server
git pull
docker-compose up -d --build
```

### Environment Variables to Set

Set these in your deployment platform (Coolify, etc.):
```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
SECRET_KEY=your-secret-key

# Optional (defaults work for most cases)
CALIBRE_LIBRARY_PATH=/opt/calibre-library-read  # Already the default
VITE_API_URL=/api  # Already the default (works with nginx proxy)
FRONTEND_URL=https://your-domain.com

# Google Drive Configuration (for cloud-stored books)
USE_GOOGLE_DRIVE=true
GOOGLE_DRIVE_CREDENTIALS_PATH=/app/credentials/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
```

### Google Drive Credentials Setup (Production)

If using Google Drive for storing books, you need to mount the service account credentials file:

**In Coolify:**
1. Go to your application → Storage → Persistent Volumes
2. Click "Add Volume"
3. Set:
   - Name: `google-drive-creds`
   - Source: Upload your `service-account.json` file
   - Mount Path: `/app/credentials/service-account.json`
   - Read Only: Yes
4. Save and redeploy

**Alternative (using secrets):**
1. Go to your application → Environment Variables
2. Create a new secret containing your service account JSON
3. Mount it as a file in the container
4. Update `GOOGLE_DRIVE_CREDENTIALS_PATH` to point to the mounted file

### Coolify Specific

In Coolify, the base `docker-compose.yml` will work out of the box:
- No need to specify `COMPOSE_FILE`
- No need to set `FRONTEND_DOCKERFILE` or `FRONTEND_PORT`
- Just set your environment variables in Coolify's UI

## Health Checks

Both frontend and backend have health checks configured:

- **Backend**: `http://localhost:8000/api/health`
- **Frontend**: Nginx serves on port 80

Monitor with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

## Troubleshooting

### Frontend shows old version
- Ensure you rebuilt: `--build` flag
- Clear browser cache
- Check no volume mounts in production config

### Backend not restarting on code changes
- This is expected in production
- Rebuild and redeploy to update

### API URL issues
- Verify `VITE_API_URL` in build args
- Frontend is built with the API URL baked in
- Rebuild frontend if API URL changes
