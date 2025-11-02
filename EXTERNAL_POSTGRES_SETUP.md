# Using External PostgreSQL Server for Deployment

This guide explains how to configure the Calibre Web Clone to use an existing PostgreSQL database on your server instead of a Docker container.

## Configuration Changes

The `docker-compose.yml` has been updated to support external PostgreSQL. The PostgreSQL service is commented out, and the connection string now uses environment variables.

## Connection String Format

```bash
# Format
postgresql+asyncpg://username:password@host:port/database

# Examples:

# Localhost (if PostgreSQL on same server)
postgresql+asyncpg://calibre:password@localhost:5432/calibre_web

# Remote server (by IP)
postgresql+asyncpg://calibre:password@192.168.1.100:5432/calibre_web

# Remote server (by hostname)
postgresql+asyncpg://calibre:password@db.example.com:5432/calibre_web

# With SSL (production)
postgresql+asyncpg://calibre:password@db.example.com:5432/calibre_web?ssl=require
```

## Environment Variables

Set these environment variables in Coolify or your deployment:

```bash
# Option 1: Full connection string (recommended)
DATABASE_URL=postgresql+asyncpg://calibre:password@your-db-server:5432/calibre_web

# Option 2: Individual components
POSTGRES_HOST=your-db-server-or-ip
POSTGRES_PORT=5432
POSTGRES_DB=calibre_web
POSTGRES_USER=calibre
POSTGRES_PASSWORD=your-password
```

## Database Setup on Server

### 1. Create Database and User

Connect to your PostgreSQL server and run:

```sql
-- Create database
CREATE DATABASE calibre_web;

-- Create user
CREATE USER calibre WITH PASSWORD 'your-secure-password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE calibre_web TO calibre;

-- If using PostgreSQL 15+, you might need:
ALTER DATABASE calibre_web OWNER TO calibre;
```

### 2. Configure PostgreSQL Access

Edit `/etc/postgresql/15/main/pg_hba.conf` (adjust version number):

```conf
# Allow connections from Docker containers
host    calibre_web    calibre    172.17.0.0/16    md5
# Or allow from specific IP
host    calibre_web    calibre    10.0.0.0/8       md5
# Or allow from localhost
host    calibre_web    calibre    127.0.0.1/32     md5
```

Edit `/etc/postgresql/15/main/postgresql.conf`:

```conf
# Allow connections from network
listen_addresses = '*'  # or specific IP

# Port (default is 5432)
port = 5432
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 3. Configure Firewall

```bash
# Allow PostgreSQL port (if needed)
sudo ufw allow 5432/tcp
# Or more restrictive:
sudo ufw allow from 172.17.0.0/16 to any port 5432
```

## Coolify Configuration

### Option 1: Full Connection String (Simplest)

In Coolify, set this environment variable:

```bash
DATABASE_URL=postgresql+asyncpg://calibre:password@your-db-server:5432/calibre_web
```

### Option 2: Individual Variables

```bash
POSTGRES_HOST=your-db-server
POSTGRES_PORT=5432
POSTGRES_DB=calibre_web
POSTGRES_USER=calibre
POSTGRES_PASSWORD=your-password
```

### Connection to Server PostgreSQL

**If Coolify and PostgreSQL on same server:**
- Use `localhost` or `127.0.0.1` as host
- Use `5432` as port (or your configured port)

**If PostgreSQL on different server:**
- Use server's IP address or hostname
- Ensure firewall allows connections
- Ensure PostgreSQL `listen_addresses` is configured

**From Docker container to host PostgreSQL:**
- Use `host.docker.internal` (Docker Desktop)
- Use `172.17.0.1` (Docker default gateway)
- Use host's actual IP address

## Testing Connection

### Test from command line:

```bash
# Test connection
psql -h your-db-server -U calibre -d calibre_web

# Test from Docker container
docker exec -it calibre-backend python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql+asyncpg://calibre:password@your-db-server:5432/calibre_web')
print('Connection successful!')
"
```

### Test from application:

```bash
# Check backend logs
docker-compose logs backend | grep -i database

# Should see:
# "Database initialized" or "Connected to database"
```

## Run Database Migrations

After configuring the connection, run migrations:

```bash
# From backend container
docker exec -it calibre-backend alembic upgrade head

# Or if using docker-compose
docker-compose exec backend alembic upgrade head
```

This will create all necessary tables in your external database.

## Security Considerations

### 1. Use Strong Passwords

```bash
# Generate secure password
openssl rand -base64 32
```

### 2. Limit Network Access

```conf
# In pg_hba.conf, restrict to specific IPs
host    calibre_web    calibre    10.0.0.50/32    md5
```

### 3. Use SSL in Production

```bash
# Connection string with SSL
DATABASE_URL=postgresql+asyncpg://calibre:password@db.example.com:5432/calibre_web?ssl=require

# Or with certificate verification
DATABASE_URL=postgresql+asyncpg://calibre:password@db.example.com:5432/calibre_web?ssl=require&sslmode=verify-full
```

### 4. Firewall Rules

Only allow PostgreSQL port from:
- Docker network (if same server)
- Application server IP (if different server)
- Your management IP (for admin access)

## Troubleshooting

### Connection Refused

**Error:** `could not connect to server: Connection refused`

**Solutions:**
1. Check PostgreSQL is running: `sudo systemctl status postgresql`
2. Check `listen_addresses` in postgresql.conf
3. Check firewall rules
4. Verify port: `sudo netstat -tulpn | grep 5432`

### Authentication Failed

**Error:** `password authentication failed for user "calibre"`

**Solutions:**
1. Verify user exists: `psql -U postgres -c "\du"`
2. Check password matches
3. Verify pg_hba.conf allows connection
4. Try resetting password: `ALTER USER calibre WITH PASSWORD 'newpassword';`

### Database Does Not Exist

**Error:** `database "calibre_web" does not exist`

**Solutions:**
1. Create database (see Database Setup above)
2. Verify database name in connection string
3. Check database exists: `psql -U postgres -l`

### Connection Timeout

**Error:** `timeout expired` or `could not connect`

**Solutions:**
1. Check network connectivity: `ping your-db-server`
2. Check firewall allows port 5432
3. Verify PostgreSQL is accessible from Docker network
4. Try using IP instead of hostname
5. Check Docker network configuration

## Migration from Docker PostgreSQL

If you previously used Docker PostgreSQL and want to migrate:

### 1. Export Data

```bash
# Export from Docker container
docker exec calibre-postgres pg_dump -U calibre calibre_web > backup.sql

# Or if container still running
docker-compose exec postgres pg_dump -U calibre calibre_web > backup.sql
```

### 2. Import to External Database

```bash
# Import to server PostgreSQL
psql -h your-db-server -U calibre -d calibre_web < backup.sql

# Or with password prompt
PGPASSWORD=password psql -h your-db-server -U calibre -d calibre_web < backup.sql
```

### 3. Update Configuration

Update `docker-compose.yml` and environment variables as shown above.

### 4. Verify

```bash
# Check data imported
psql -h your-db-server -U calibre -d calibre_web -c "SELECT COUNT(*) FROM users;"

# Restart backend
docker-compose restart backend

# Check logs
docker-compose logs backend | grep -i database
```

## Example: Complete Setup

### Server PostgreSQL (Ubuntu/Debian)

```bash
# Install PostgreSQL (if not already installed)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE calibre_web;
CREATE USER calibre WITH PASSWORD 'secure-password-here';
GRANT ALL PRIVILEGES ON DATABASE calibre_web TO calibre;
\q

# Configure access
sudo nano /etc/postgresql/15/main/pg_hba.conf
# Add: host    calibre_web    calibre    0.0.0.0/0    md5

sudo nano /etc/postgresql/15/main/postgresql.conf
# Set: listen_addresses = '*'

# Restart
sudo systemctl restart postgresql
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      DATABASE_URL: postgresql+asyncpg://calibre:secure-password-here@172.17.0.1:5432/calibre_web
      # Or use environment variable
      # DATABASE_URL: ${DATABASE_URL}
```

### Coolify Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://calibre:secure-password-here@your-server-ip:5432/calibre_web
```

## Benefits of External PostgreSQL

✅ **Shared Database** - Multiple applications can use same PostgreSQL instance  
✅ **Better Performance** - Direct filesystem access (no Docker overhead)  
✅ **Easier Backups** - Standard PostgreSQL backup tools  
✅ **Professional Setup** - Can configure replication, clustering  
✅ **Resource Management** - Better control over database resources  

## Next Steps

1. ✅ Set up database and user on server
2. ✅ Configure PostgreSQL access (pg_hba.conf, postgresql.conf)
3. ✅ Set firewall rules
4. ✅ Update environment variables
5. ✅ Run migrations
6. ✅ Test connection
7. ✅ Deploy!

