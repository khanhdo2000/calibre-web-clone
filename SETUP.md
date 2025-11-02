# Setup Guide

This guide will help you set up and run the Calibre Web Clone application.

## Prerequisites

### For Docker Setup (Recommended)
- Docker Desktop or Docker Engine
- Docker Compose
- Your Calibre library directory path

### For Manual Setup
- Python 3.11+
- Node.js 18+
- Redis
- Your Calibre library directory path

## Quick Start with Docker

### 1. Configure Your Calibre Library Path

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and set your Calibre library path:

```env
CALIBRE_LIBRARY_PATH=/path/to/your/calibre/library
```

**Examples:**
- macOS: `CALIBRE_LIBRARY_PATH=/Users/yourname/Calibre Library`
- Linux: `CALIBRE_LIBRARY_PATH=/home/yourname/Calibre Library`
- Windows: `CALIBRE_LIBRARY_PATH=C:/Users/yourname/Calibre Library`

### 2. Build and Start Services

```bash
# Build the Docker images
docker-compose build

# Start all services
docker-compose up -d
```

Or use the Makefile:

```bash
make build
make up
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 4. View Logs

```bash
docker-compose logs -f
```

Or:

```bash
make logs
```

### 5. Stop Services

```bash
docker-compose down
```

Or:

```bash
make down
```

## Manual Setup

### 1. Start Redis

```bash
docker run -d -p 6379:6379 redis:alpine
```

Or install and start Redis locally.

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set CALIBRE_LIBRARY_PATH

# Run the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Setup Frontend

In a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Run the frontend
npm run dev
```

The frontend will be available at http://localhost:3000 (or the port shown in the terminal).

## Verifying Your Setup

### 1. Check Backend Health

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "cache": true
}
```

### 2. Check Calibre Library Connection

```bash
curl http://localhost:8000/api/books/?per_page=1
```

You should see book data from your Calibre library.

### 3. Open Frontend

Navigate to http://localhost:3000 and you should see your books displayed.

## Troubleshooting

### "Calibre database not found"

**Problem**: The backend can't find your `metadata.db` file.

**Solution**:
1. Verify your Calibre library path in `.env`
2. Ensure the path contains a `metadata.db` file
3. Check file permissions (the application needs read access)
4. If using Docker, ensure the volume mount is correct

### "Failed to connect to Redis"

**Problem**: The backend can't connect to Redis.

**Solution**:
1. Ensure Redis is running: `docker ps` or `redis-cli ping`
2. Check the `REDIS_URL` in your `.env` file
3. If using Docker, ensure the Redis container is healthy

### Books not showing up

**Problem**: The frontend loads but shows no books.

**Solution**:
1. Check backend logs: `docker-compose logs backend`
2. Verify the Calibre library has books
3. Check that metadata.db is not corrupted (open it with a SQLite browser)
4. Clear Redis cache: `docker-compose restart redis`

### Cover images not loading

**Problem**: Books display but covers are missing.

**Solution**:
1. Verify cover images exist in your Calibre library (e.g., `BookPath/cover.jpg`)
2. Check file permissions
3. Check browser console for CORS errors

### EPUB reader not working

**Problem**: "Read" button doesn't work or reader fails to load.

**Solution**:
1. Verify the book has an EPUB format
2. Check browser console for errors
3. Ensure the file exists and is readable
4. Try downloading the EPUB first to verify it's not corrupted

## Configuration Options

### Backend Environment Variables

Edit `backend/.env`:

```env
# Required
CALIBRE_LIBRARY_PATH=/path/to/calibre/library

# Optional
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600                    # Cache time in seconds
API_HOST=0.0.0.0
API_PORT=8000
MAX_SEARCH_RESULTS=100
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend Environment Variables

Edit `frontend/.env`:

```env
# Optional - defaults to /api (uses proxy)
VITE_API_URL=http://localhost:8000/api
```

## Performance Tuning

### Increase Cache TTL

For better performance with large libraries, increase the cache time:

```env
CACHE_TTL=7200  # 2 hours
```

### Adjust Results Per Page

Modify the frontend to show more books per page by editing:
- `frontend/src/pages/HomePage.tsx`: Change `perPage` constant

### Redis Memory

For very large libraries, increase Redis memory in `docker-compose.yml`:

```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

## Production Deployment

For production deployment:

1. Use environment variables for sensitive data
2. Enable HTTPS with a reverse proxy (nginx, Traefik, Caddy)
3. Set stronger CORS restrictions
4. Use Redis persistence
5. Set up monitoring and logging
6. Consider using a CDN for static assets
7. Regular backups of your Calibre library

## Updating

To update the application:

```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

## Support

For issues and questions:
- Check the logs: `docker-compose logs -f`
- Review this troubleshooting guide
- Check that your Calibre library is valid and accessible
