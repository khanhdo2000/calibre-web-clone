# Deploying Calibre Web Clone with Coolify

This guide walks you through deploying the Calibre Web Clone application using Coolify.

## Prerequisites

- Coolify installed and running on your server
- A Git repository containing this project
- Access to the server where you'll store your Calibre library

## Deployment Options

### Option 1: Docker Compose Stack (Recommended)

Coolify can deploy a complete Docker Compose stack with all services (PostgreSQL, Redis, Backend, Frontend).

#### Step 1: Create a New Project

1. Log in to your Coolify dashboard
2. Go to **Projects** → Click **+ Add**
3. Name your project (e.g., "Calibre Web Clone")

#### Step 2: Add Docker Compose Stack

1. In your project, click **+ Add New Resource**
2. Select **Docker Compose Stack**
3. Configure the deployment:
   - **Name**: `calibre-web-clone`
   - **Source**: Connect your Git repository
   - **Branch**: `main` (or your deployment branch)
   - **Docker Compose File**: `docker-compose.yml`

#### Step 3: Configure Environment Variables

In Coolify, set these environment variables for the stack:

```bash
# PostgreSQL
POSTGRES_PASSWORD=<generate-strong-password>

# Backend
SECRET_KEY=<generate-strong-secret-key>
CALIBRE_LIBRARY_PATH=/calibre-library
WATCH_CALIBRE_DB=true

# Database Connection (will use internal postgres service)
DATABASE_URL=postgresql+asyncpg://calibre:<POSTGRES_PASSWORD>@postgres:5432/calibre_web

# Redis (will use internal redis service)
REDIS_URL=redis://redis:6379

# API
API_HOST=0.0.0.0
API_PORT=8000

# CORS - Update with your domain
CORS_ORIGINS=https://your-domain.com,http://your-domain.com

# Optional: Google Drive
USE_GOOGLE_DRIVE=false
GOOGLE_DRIVE_CREDENTIALS_PATH=/credentials.json

# Optional: S3
USE_S3_COVERS=false
```

#### Step 4: Configure Volumes

In the Docker Compose stack settings, you'll need to handle volumes:

1. **Calibre Library Volume**:
   - Type: `bind mount`
   - Host path: `/path/to/your/calibre/library` (on your server)
   - Container path: `/calibre-library`
   - Service: `backend`

2. **Database and Cache Volumes**:
   - These are managed volumes (postgres-data, redis-data) and Coolify will handle them automatically

#### Step 5: Configure Ports and Domains

1. **Frontend Service**:
   - Internal port: `80`
   - Add a domain in Coolify: e.g., `calibre.yourdomain.com`
   - Coolify will automatically set up reverse proxy and SSL

2. **Backend API** (if you want external access):
   - Internal port: `8000`
   - Add a domain: e.g., `api.calibre.yourdomain.com`
   - Or access via frontend's domain with `/api` prefix

#### Step 6: Deploy

1. Click **Deploy** or **Save & Deploy**
2. Coolify will:
   - Clone your repository
   - Build the Docker images
   - Start all services
   - Set up the reverse proxy
   - Configure SSL certificates (Let's Encrypt)

---

### Option 2: Separate Services (Advanced)

If you prefer to deploy services separately:

#### Backend Service

1. **Resource Type**: Docker Compose or Standalone Docker
2. **Build Context**: `./backend`
3. **Dockerfile**: `backend/Dockerfile`
4. **Port**: `8000`
5. **Environment Variables**: See above

#### Frontend Service

1. **Resource Type**: Docker Compose or Standalone Docker
2. **Build Context**: `./frontend`
3. **Dockerfile**: `frontend/Dockerfile`
4. **Port**: `80`
5. **Environment Variables**:
   ```bash
   VITE_API_URL=https://api.calibre.yourdomain.com/api
   ```

#### Database Services

Use Coolify's managed databases:
- **PostgreSQL**: Create a PostgreSQL database resource
- **Redis**: Create a Redis database resource

Then update backend environment variables to use these services.

---

## Important Considerations

### 1. Calibre Library Access

The Calibre library must be accessible from the backend container. Options:

- **Bind Mount** (Recommended for local files):
  ```yaml
  volumes:
    - /host/path/to/calibre-library:/calibre-library
  ```

- **Network Storage** (NFS/SMB):
  Mount network storage on the server, then bind mount to container

- **Cloud Storage** (Google Drive):
  Use the Google Drive integration instead of local filesystem

### 2. Environment Variables for Frontend

The frontend is built at **build time**, so you need to rebuild if you change:
- `VITE_API_URL`

Update the frontend Dockerfile or use Coolify's build-time environment variables.

### 3. Database Migrations

On first deployment, run Alembic migrations:

```bash
# In Coolify, execute in backend container:
docker exec calibre-backend alembic upgrade head
```

Or add this to your deployment process.

### 4. Persistent Volumes

Ensure these volumes persist:
- `postgres-data`: PostgreSQL data
- `redis-data`: Redis persistence
- Calibre library mount

### 5. Health Checks

Coolify uses the health checks defined in `docker-compose.yml`. Make sure they're working:
- Backend: `http://localhost:8000/api/health`
- Postgres: `pg_isready`
- Redis: `redis-cli ping`

---

## Post-Deployment Configuration

### 1. Verify Services

1. Check all services are running in Coolify dashboard
2. View logs for any errors
3. Test the health endpoints

### 2. Access the Application

1. Frontend: `https://calibre.yourdomain.com`
2. API Health: `https://calibre.yourdomain.com/api/health`
3. API Docs: `https://calibre.yourdomain.com/api/docs`

### 3. Create Admin User

You'll need to create the first admin user. Options:

- Use Coolify's terminal to execute:
  ```bash
  docker exec -it calibre-backend python -c "from app.services.auth import create_user; ..."
  ```

- Or create an admin endpoint for initial setup

### 4. SSL Certificates

Coolify automatically configures SSL via Let's Encrypt. Ensure:
- Your domain DNS points to the server
- Ports 80 and 443 are accessible

---

## Troubleshooting

### Services Won't Start

1. Check Coolify logs for build errors
2. Verify environment variables are set correctly
3. Check volume mounts are accessible

### Database Connection Errors

1. Verify `DATABASE_URL` is correct
2. Check PostgreSQL service is running
3. Ensure `depends_on` is configured correctly

### Frontend Can't Reach Backend

1. Check `VITE_API_URL` matches your deployment
2. Verify CORS settings include your frontend domain
3. Check nginx proxy configuration in frontend container

### Calibre Library Not Found

1. Verify the library path is correct
2. Check file permissions on the host
3. Ensure the volume mount is configured

---

## Updating the Application

### Automatic Deployments

Configure in Coolify:
1. Go to your resource → **Settings** → **Deployments**
2. Enable **Auto Deploy**
3. Choose trigger (webhook, schedule, etc.)

### Manual Updates

1. Push changes to your Git repository
2. In Coolify, go to your resource
3. Click **Deploy** to rebuild and restart

---

## Security Best Practices

1. **Generate Strong Secrets**:
   ```bash
   # SECRET_KEY (32+ characters)
   openssl rand -hex 32
   
   # POSTGRES_PASSWORD (strong password)
   openssl rand -base64 24
   ```

2. **Limit CORS Origins**: Only include your actual domains

3. **Use Environment Variables**: Never commit secrets to Git

4. **Enable SSL**: Always use HTTPS in production

5. **Firewall Rules**: Restrict database ports (5432, 6379) to internal network only

---

## Example Coolify Configuration

Here's a quick reference for setting up in Coolify:

```
Project: Calibre Web Clone
Resource Type: Docker Compose Stack
Repository: your-git-repo
Branch: main
Docker Compose File: docker-compose.yml
Port Mappings:
  - Frontend: 80 → calibre.yourdomain.com
  - Backend: 8000 (internal only, or api.calibre.yourdomain.com)
Volumes:
  - postgres-data (managed)
  - redis-data (managed)
  - /server/path/calibre-library → /calibre-library (bind)
Environment Variables: [see Step 3 above]
SSL: Auto (Let's Encrypt)
```

---

## Additional Resources

- [Coolify Documentation](https://coolify.io/docs)
- [Docker Compose in Coolify](https://coolify.io/docs/get-started/quickstart)
- [Environment Variables Guide](https://coolify.io/docs/configuration/environment-variables)

---

## Quick Deploy Script

For automated deployment, you can create a GitHub Actions workflow or use Coolify's webhook feature to auto-deploy on push to main branch.

