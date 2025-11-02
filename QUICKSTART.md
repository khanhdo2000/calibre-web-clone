# Quick Start Guide - Configured for Your System

Your Calibre library has been detected at: `/Users/khanhdo/calibre-web`
- ✅ metadata.db found (1.2 MB)
- ✅ Books organized by author
- ✅ Configuration files created

## Step 1: Start the System

```bash
cd /Users/khanhdo/dev/calibre-web-clone-c

# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# Watch the logs
docker-compose logs -f
```

**Wait for these messages**:
```
✓ PostgreSQL database started
✓ Redis cache connected
✓ Database initialized
✓ Started watching Calibre database
✓ Backend started on port 8000
✓ Frontend started on port 3000
```

## Step 2: Create Your Admin Account

```bash
# Open a new terminal
cd /Users/khanhdo/dev/calibre-web-clone-c

# Create admin user
docker-compose exec backend python << 'EOF'
import asyncio
from app.services.auth import auth_service
from app.database import async_session_maker

async def create_admin():
    async with async_session_maker() as db:
        user = await auth_service.create_user(
            db=db,
            email='admin@example.com',
            username='admin',
            password='changeme123',
            full_name='Admin User',
            is_admin=True
        )
        print(f'\n✓ Created admin user:')
        print(f'  Email: {user.email}')
        print(f'  Username: {user.username}')
        print(f'  Password: changeme123')
        print(f'\nPlease change the password after first login!')

asyncio.run(create_admin())
EOF
```

## Step 3: Access the Application

Open your browser:

1. **Frontend**: http://localhost:3000
2. **API Documentation**: http://localhost:8000/docs
3. **Health Check**: http://localhost:8000/api/health

**Login with**:
- Email: `admin@example.com`
- Password: `changeme123`

## Step 4: Test Calibre Desktop Sync

1. Keep the web app running
2. Open Calibre desktop
3. Add a new book or edit metadata
4. Wait 2-3 seconds
5. Refresh the web interface → **Changes appear automatically!**

## Your Current Configuration

### Local Storage (Default)
- ✅ Books: `/Users/khanhdo/calibre-web`
- ✅ Covers: Local filesystem
- ✅ Database: Calibre's metadata.db

### Services Running
```
┌─────────────────────────────────────────┐
│ Frontend (React)     → Port 3000        │
└─────────────────────────────────────────┘
           │
┌─────────────────────────────────────────┐
│ Backend (FastAPI)    → Port 8000        │
└─────────────────────────────────────────┘
           │
┌─────────────┬─────────────┬─────────────┐
│ PostgreSQL  │   Redis     │  Calibre    │
│ (Users)     │  (Cache)    │  (Books)    │
│ Port 5432   │  Port 6379  │  Local      │
└─────────────┴─────────────┴─────────────┘
```

## Common Commands

```bash
# View logs
docker-compose logs -f backend    # Backend logs
docker-compose logs -f frontend   # Frontend logs

# Restart services
docker-compose restart

# Stop everything
docker-compose down

# Stop and remove data (WARNING: deletes user data!)
docker-compose down -v

# Check service health
curl http://localhost:8000/api/health
```

## Testing the API

```bash
# Login and get token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=changeme123"

# Save the access_token from response

# Get books (replace YOUR_TOKEN)
curl http://localhost:8000/api/books/?per_page=5 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search books
curl "http://localhost:8000/api/books/search/?q=python" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Next Steps

### Option 1: Keep It Simple (Current Setup)
✅ Everything runs locally
✅ Books and covers on filesystem
✅ Perfect for personal use

### Option 2: Add Google Drive Storage
📚 Store books in Google Drive to save local space
📖 See: `PRODUCTION_GUIDE.md` → Google Drive Setup

### Option 3: Add S3 Cover Storage
🖼️ Store covers in S3 for better scalability
📖 See: `PRODUCTION_GUIDE.md` → S3 Cover Storage Setup

## Troubleshooting

### Port Already in Use

```bash
# If port 3000, 5432, 6379, or 8000 is already in use:
# Edit docker-compose.yml and change the ports:

# Example: Change frontend from 3000 to 3001
ports:
  - "3001:80"  # Change left side only
```

### Can't See Books

```bash
# Check if metadata.db is accessible
ls -lh /Users/khanhdo/calibre-web/metadata.db

# Check backend logs
docker-compose logs backend | grep -i error

# Verify path in container
docker-compose exec backend ls -la /calibre-library/
```

### File Watcher Not Working

```bash
# Check watcher status
docker-compose logs backend | grep -i watcher

# Should see: "Started watching Calibre database"

# Manually trigger cache clear
docker-compose exec redis redis-cli FLUSHDB
```

### Reset Everything

```bash
# Stop and remove all data
docker-compose down -v

# Remove .env files (will regenerate)
rm .env backend/.env

# Start fresh
docker-compose up -d
```

## Performance Tips

Your library appears to have 130+ authors. Here are some tips:

1. **Increase cache TTL** (if books don't change often):
   ```env
   # .env
   CACHE_TTL=7200  # 2 hours instead of 1
   ```

2. **Monitor Redis memory**:
   ```bash
   docker-compose exec redis redis-cli INFO memory
   ```

3. **Check cache hit rate**:
   ```bash
   docker-compose logs backend | grep "Cache hit"
   ```

## Support

- 📖 Full documentation: `PRODUCTION_GUIDE.md`
- 🏗️ Architecture details: `ARCHITECTURE.md`
- 🔧 Setup guide: `SETUP.md`
- 🐛 Issues: Check logs with `docker-compose logs -f`

---

**Ready to start?**

```bash
docker-compose up -d
```

Then visit: http://localhost:3000
