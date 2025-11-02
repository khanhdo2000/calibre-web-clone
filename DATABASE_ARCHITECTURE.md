# Database Architecture: Shared vs Separate Instances

## Option 1: One PostgreSQL Instance, Multiple Databases ✅ **RECOMMENDED**

### Architecture
```
┌─────────────────────────────────────────┐
│  Single PostgreSQL Server              │
│  (One Container/Process)               │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ Database 1   │  │ Database 2   │   │
│  │ (calibre_web)│  │ (app2_db)    │   │
│  └──────────────┘  └──────────────┘   │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ Database 3   │  │ Database 4   │   │
│  │ (app3_db)    │  │ (app4_db)    │   │
│  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────┘
```

### Advantages
1. ✅ **Resource Efficient**: 
   - Single PostgreSQL process
   - Shared memory, connection pool
   - Lower RAM usage (one instance overhead)

2. ✅ **Easier Management**:
   - One container to backup/update
   - Single point of monitoring
   - Unified logging

3. ✅ **Cost Effective**:
   - Lower memory footprint
   - Single port to manage
   - Shared buffer cache

4. ✅ **Database Isolation**:
   - Each app has its own database
   - Users/permissions separated per database
   - Schema isolation (apps can't see each other's tables)

5. ✅ **Performance**:
   - Shared connection pool benefits
   - Better resource utilization
   - PostgreSQL handles multiple databases efficiently

### Disadvantages
1. ❌ **Single Point of Failure**: 
   - If PostgreSQL crashes, all apps affected
   - Mitigated by: proper backups, health checks

2. ❌ **Resource Contention**:
   - High load from one app can affect others
   - Mitigated by: connection limits per database

3. ❌ **Upgrade Dependency**:
   - All apps upgrade together
   - Mitigated by: version pinning, testing

### Configuration Example

**docker-compose.yml:**
```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: shared-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      # Multiple databases via init script
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./init-multiple-dbs.sh:/docker-entrypoint-initdb.d/init-multiple-dbs.sh
    ports:
      - "5432:5432"
```

**init-multiple-dbs.sh:**
```bash
#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE calibre_web;
    CREATE USER calibre WITH PASSWORD 'calibre_password';
    GRANT ALL PRIVILEGES ON DATABASE calibre_web TO calibre;
    
    CREATE DATABASE app2_db;
    CREATE USER app2_user WITH PASSWORD 'app2_password';
    GRANT ALL PRIVILEGES ON DATABASE app2_db TO app2_user;
    
    CREATE DATABASE app3_db;
    CREATE USER app3_user WITH PASSWORD 'app3_password';
    GRANT ALL PRIVILEGES ON DATABASE app3_db TO app3_user;
EOSQL
```

**Connection Strings:**
```bash
# App 1 (Calibre Web)
DATABASE_URL=postgresql+asyncpg://calibre:password@shared-postgres:5432/calibre_web

# App 2
DATABASE_URL=postgresql+asyncpg://app2_user:password@shared-postgres:5432/app2_db

# App 3
DATABASE_URL=postgresql+asyncpg://app3_user:password@shared-postgres:5432/app3_db
```

---

## Option 2: Separate PostgreSQL Instances

### Architecture
```
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ PostgreSQL 1   │  │ PostgreSQL 2   │  │ PostgreSQL 3   │
│ (calibre_web)  │  │ (app2_db)      │  │ (app3_db)      │
│ Port: 5432     │  │ Port: 5433     │  │ Port: 5434     │
└────────────────┘  └────────────────┘  └────────────────┘
```

### Advantages
1. ✅ **Complete Isolation**:
   - No interference between apps
   - Independent upgrades
   - Separate resource limits

2. ✅ **Fault Isolation**:
   - One app's database crash doesn't affect others
   - Independent backups/restores

3. ✅ **Custom Configuration**:
   - Different PostgreSQL versions
   - App-specific tuning (shared_buffers, etc.)

### Disadvantages
1. ❌ **Resource Overhead**:
   - Multiple PostgreSQL processes
   - Higher RAM usage (~50MB per instance)
   - More ports to manage

2. ❌ **Management Overhead**:
   - Multiple containers to backup
   - More complex monitoring
   - More Docker resources

3. ❌ **Less Efficient**:
   - Each instance has its own buffer cache
   - Can't share connections efficiently

### Configuration Example

**docker-compose.yml:**
```yaml
services:
  postgres-calibre:
    image: postgres:15-alpine
    container_name: calibre-postgres
    environment:
      POSTGRES_DB: calibre_web
      POSTGRES_USER: calibre
      POSTGRES_PASSWORD: ${CALIBRE_POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - calibre-postgres-data:/var/lib/postgresql/data

  postgres-app2:
    image: postgres:15-alpine
    container_name: app2-postgres
    environment:
      POSTGRES_DB: app2_db
      POSTGRES_USER: app2_user
      POSTGRES_PASSWORD: ${APP2_POSTGRES_PASSWORD}
    ports:
      - "5433:5432"
    volumes:
      - app2-postgres-data:/var/lib/postgresql/data

volumes:
  calibre-postgres-data:
  app2-postgres-data:
```

---

## Recommendation Matrix

| Scenario | Recommended Approach |
|----------|---------------------|
| **2-5 small apps** | ✅ One instance, multiple databases |
| **6-10 apps** | ✅ One instance, multiple databases |
| **High-load apps** | ⚠️ Separate instances for critical apps |
| **Different versions needed** | ❌ Separate instances |
| **Different backup schedules** | ⚠️ Can still use shared (pg_dump per DB) |
| **Development/Testing** | ✅ One instance (easier) |
| **Production with strict isolation** | ⚠️ Separate instances |
| **Resource-constrained server** | ✅ One instance |

---

## Best Practices for Shared Database Instance

### 1. Connection Limits Per Database
```sql
-- Limit connections per database
ALTER DATABASE calibre_web CONNECTION LIMIT 50;
ALTER DATABASE app2_db CONNECTION LIMIT 30;
```

### 2. User Permissions
```sql
-- Each app user can only access their database
REVOKE ALL ON DATABASE app2_db FROM calibre;
REVOKE ALL ON DATABASE calibre_web FROM app2_user;
```

### 3. Resource Monitoring
```sql
-- Check active connections per database
SELECT 
    datname, 
    count(*) as connections,
    max_conn
FROM pg_stat_activity 
JOIN pg_database ON pg_stat_activity.datid = pg_database.oid
GROUP BY datname, max_conn;
```

### 4. Connection Pooling (PgBouncer)
For high-concurrency apps, add PgBouncer:
```yaml
services:
  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    environment:
      DATABASES_HOST: postgres
      DATABASES_PORT: 5432
      DATABASES_USER: postgres
      DATABASES_PASSWORD: ${POSTGRES_PASSWORD}
      DATABASES_DBNAME: calibre_web,app2_db
    ports:
      - "6432:6432"
```

### 5. Backup Strategy
```bash
# Backup specific database
pg_dump -U calibre -d calibre_web > calibre_web_backup.sql

# Backup all databases
for db in $(psql -U postgres -t -c "SELECT datname FROM pg_database WHERE datistemplate = false"); do
    pg_dump -U postgres $db > ${db}_backup.sql
done
```

---

## Coolify-Specific Considerations

### For Coolify Deployment:

**Shared Database Instance:**
1. Create one PostgreSQL resource in Coolify
2. Add multiple databases manually or via init script
3. Each app connects to same PostgreSQL service with different database names

**Separate Instances:**
1. Create separate PostgreSQL resources for each app
2. Each app gets its own managed database
3. More resources but better isolation

### Coolify Configuration Example

**Shared Instance Approach:**
```
Project: Main Infrastructure
├── PostgreSQL (shared-postgres)
│   ├── Database: calibre_web
│   ├── Database: app2_db
│   └── Database: app3_db
│
Project: Calibre Web
├── Application: backend
│   └── DATABASE_URL=postgresql://...@shared-postgres:5432/calibre_web
└── Application: frontend
```

---

## Performance Comparison

### Resource Usage (5 apps)

| Metric | One Instance | Separate Instances |
|--------|-------------|-------------------|
| RAM (idle) | ~150 MB | ~250 MB (50MB × 5) |
| RAM (active) | ~300 MB | ~500 MB |
| CPU (idle) | ~0.5% | ~2.5% (0.5% × 5) |
| Disk (data) | Same | Same (data size) |
| Disk (overhead) | ~50 MB | ~250 MB |

### Scaling Considerations

- **One Instance**: Scales by adding more databases, connection pooling
- **Separate Instances**: Scales by adding more containers, but more overhead

---

## Migration Strategy

### Moving from Separate to Shared:
```bash
# 1. Dump existing databases
pg_dump -U calibre -d calibre_web > calibre_web.sql
pg_dump -U app2_user -d app2_db > app2_db.sql

# 2. Create new shared PostgreSQL
docker-compose up -d shared-postgres

# 3. Import to shared instance
psql -U calibre -d calibre_web < calibre_web.sql
psql -U app2_user -d app2_db < app2_db.sql

# 4. Update connection strings
# 5. Test and switch
```

---

## Final Recommendation

**For most use cases**: Use **one PostgreSQL instance with multiple databases** because:

1. ✅ More efficient resource usage
2. ✅ Easier management and monitoring
3. ✅ PostgreSQL handles isolation well
4. ✅ Sufficient for most workloads
5. ✅ Can migrate to separate instances later if needed

**Use separate instances only if**:
- Apps need different PostgreSQL versions
- Strict security/compliance requires complete isolation
- One app has extremely high load that affects others
- You need app-specific PostgreSQL tuning

---

## Example: Shared Instance Setup Script

Create `init-multiple-dbs.sh`:
```bash
#!/bin/bash
set -e

# Create databases and users
for app in calibre_web app2_db app3_db; do
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE ${app};
        CREATE USER ${app}_user WITH PASSWORD '${app}_password';
        GRANT ALL PRIVILEGES ON DATABASE ${app} TO ${app}_user;
        ALTER DATABASE ${app} CONNECTION LIMIT 50;
EOSQL
done
```

This gives you the best of both worlds: efficiency with isolation.

