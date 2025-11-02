# Calibre Library Sync Scripts

Scripts to sync your local Calibre library to the remote server.

## Prerequisites

1. **SSH Access**: Set up SSH key authentication
   ```bash
   ssh-keygen -t rsa
   ssh-copy-id root@31.97.70.110
   ```

2. **rsync**: Install rsync (usually pre-installed on macOS/Linux)
   ```bash
   # macOS
   brew install rsync
   
   # Linux
   sudo apt-get install rsync
   ```

## Usage

### Bash Script (Simple)

```bash
# Make executable
chmod +x scripts/sync_calibre_library.sh

# Run sync
./scripts/sync_calibre_library.sh
```

### Python Script (Advanced)

```bash
# Make executable
chmod +x scripts/sync_calibre_library.py

# Basic sync
python3 scripts/sync_calibre_library.py

# Custom options
python3 scripts/sync_calibre_library.py \
  --remote-host root@31.97.70.110 \
  --remote-path /opt/calibre-library \
  --local-path ./calibre-library

# Dry run (see what would be synced)
python3 scripts/sync_calibre_library.py --dry-run

# Skip Docker restart prompt
python3 scripts/sync_calibre_library.py --no-restart
```

## Configuration

Edit the script or use environment variables:

```bash
# Set custom paths
export CALIBRE_LOCAL_PATH="./my-calibre-library"
export CALIBRE_REMOTE_PATH="/custom/path/on/server"

./scripts/sync_calibre_library.sh
```

## What Gets Synced

- All book files (EPUB, PDF, MOBI, etc.)
- Metadata database (`metadata.db`)
- Book covers
- Calibre library structure

## What's Excluded

- Temporary files (`.tmp`, `.bak`)
- System files (`.DS_Store`, `Thumbs.db`)
- Build artifacts

## Server Setup

1. **Create directory on server:**
   ```bash
   ssh root@31.97.70.110 "mkdir -p /opt/calibre-library && chmod 755 /opt/calibre-library"
   ```

2. **Set environment variable in docker-compose:**
   ```bash
   CALIBRE_LIBRARY_PATH=/opt/calibre-library
   ```

3. **Or update docker-compose.yml directly:**
   ```yaml
   volumes:
     - /opt/calibre-library:/calibre-library:ro
   ```

## Troubleshooting

### SSH Connection Issues

```bash
# Test connection
ssh root@31.97.70.110

# Check SSH key
ssh-add -l

# Re-copy SSH key
ssh-copy-id root@31.97.70.110
```

### Permission Issues

```bash
# On server, ensure directory is writable
ssh root@31.97.70.110 "chmod 755 /opt/calibre-library"
```

### rsync Not Found

Install rsync:
- macOS: `brew install rsync`
- Linux: `sudo apt-get install rsync`
- Windows: Use WSL or install via Git Bash

## Automated Sync

Add to crontab for automatic syncing:

```bash
# Edit crontab
crontab -e

# Sync every day at 2 AM
0 2 * * * /path/to/calibre-web-clone/scripts/sync_calibre_library.sh
```

## Security Notes

- Use SSH keys, not passwords
- Consider using a non-root user for better security
- The library is mounted read-only (`:ro`) in Docker for safety

