# Calibre Library Sync Guide

Quick guide to sync your local Calibre library to the server.

## Quick Start

### 1. Set up SSH access (one-time)

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy key to server
ssh-copy-id root@31.97.70.110

# Test connection
ssh root@31.97.70.110
```

### 2. Create library directory on server

```bash
ssh root@31.97.70.110 "mkdir -p /opt/calibre-library && chmod 755 /opt/calibre-library"
```

### 3. Sync your library

```bash
# Using bash script
./scripts/sync_calibre_library.sh

# Or using Python script (more features)
python3 scripts/sync_calibre_library.py
```

### 4. Configure Docker on server

Set environment variable in Coolify or docker-compose:

```bash
CALIBRE_LIBRARY_PATH=/opt/calibre-library
```

Or update `docker-compose.yml` on server:

```yaml
volumes:
  - /opt/calibre-library:/calibre-library:ro
```

## Docker Configuration

The `docker-compose.yml` is configured to:
- Use `/opt/calibre-library` as default path (server deployment)
- Mount as read-only (`:ro`) for safety
- Allow override via `CALIBRE_LIBRARY_PATH` environment variable

### Local Development

```bash
export CALIBRE_LIBRARY_PATH=./calibre-library
docker-compose up
```

### Server Deployment

```bash
export CALIBRE_LIBRARY_PATH=/opt/calibre-library
docker-compose up
```

## Script Options

### Bash Script

```bash
./scripts/sync_calibre_library.sh
```

### Python Script (Advanced)

```bash
# Basic sync
python3 scripts/sync_calibre_library.py

# Custom server path
python3 scripts/sync_calibre_library.py \
  --remote-path /custom/path/on/server

# Dry run (see what would sync)
python3 scripts/sync_calibre_library.py --dry-run

# Custom SSH port
python3 scripts/sync_calibre_library.py --ssh-port 2222
```

## Server Setup Checklist

- [ ] SSH key authentication set up
- [ ] Directory created: `/opt/calibre-library`
- [ ] Directory permissions: `chmod 755 /opt/calibre-library`
- [ ] Docker volume configured
- [ ] First sync completed
- [ ] Docker containers restarted

## Automated Sync (Optional)

Add to crontab for daily sync:

```bash
crontab -e

# Add this line (syncs every day at 2 AM)
0 2 * * * cd /path/to/calibre-web-clone && ./scripts/sync_calibre_library.sh >> /tmp/calibre-sync.log 2>&1
```

## Troubleshooting

**SSH connection fails:**
```bash
# Test connection
ssh -v root@31.97.70.110

# Check SSH key
ssh-add -l
```

**Permission denied on server:**
```bash
ssh root@31.97.70.110 "ls -la /opt/calibre-library"
```

**Docker can't read library:**
```bash
# Check permissions
ssh root@31.97.70.110 "ls -la /opt/calibre-library"

# Ensure readable
ssh root@31.97.70.110 "chmod -R 755 /opt/calibre-library"
```

