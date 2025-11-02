#!/bin/bash

# Sync Calibre Library to Remote Server
# Usage: ./scripts/sync_calibre_library.sh [options]

set -e

# Configuration
REMOTE_HOST="root@31.97.70.110"
REMOTE_PATH="/opt/calibre-library"
LOCAL_PATH="./calibre-library"
SSH_PORT="${SSH_PORT:-22}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if local library exists
if [ ! -d "$LOCAL_PATH" ]; then
    print_error "Local Calibre library not found at: $LOCAL_PATH"
    exit 1
fi

# Test SSH connection
print_info "Testing SSH connection to $REMOTE_HOST..."
if ! ssh -p $SSH_PORT -o ConnectTimeout=5 -o BatchMode=yes "$REMOTE_HOST" exit 2>/dev/null; then
    print_warn "SSH connection test failed. Make sure:"
    print_warn "  1. SSH key is set up (ssh-keygen -t rsa)"
    print_warn "  2. SSH key is added to server: ssh-copy-id $REMOTE_HOST"
    print_warn "  3. You can connect manually: ssh $REMOTE_HOST"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create remote directory if it doesn't exist
print_info "Ensuring remote directory exists: $REMOTE_PATH"
ssh -p $SSH_PORT "$REMOTE_HOST" "mkdir -p $REMOTE_PATH && chmod 755 $REMOTE_PATH"

# Sync files using rsync (faster and more efficient than scp)
print_info "Syncing Calibre library to $REMOTE_HOST:$REMOTE_PATH"
print_info "This may take a while depending on library size..."

rsync -avz --progress \
    -e "ssh -p $SSH_PORT" \
    --exclude='*.tmp' \
    --exclude='*.bak' \
    --exclude='.DS_Store' \
    --exclude='Thumbs.db' \
    --delete \
    "$LOCAL_PATH/" "$REMOTE_HOST:$REMOTE_PATH/"

if [ $? -eq 0 ]; then
    print_info "Sync completed successfully!"
    print_info "Library synced to: $REMOTE_HOST:$REMOTE_PATH"
    
    # Show library info
    print_info "Library statistics:"
    ssh -p $SSH_PORT "$REMOTE_HOST" "du -sh $REMOTE_PATH && echo 'Files:' && find $REMOTE_PATH -type f | wc -l"
else
    print_error "Sync failed!"
    exit 1
fi

# Optional: Restart Docker containers on server
read -p "Restart Docker containers on server? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Restarting Docker containers..."
    ssh -p $SSH_PORT "$REMOTE_HOST" "cd /path/to/your/app && docker-compose restart backend || echo 'Docker restart skipped (update path in script)'"
fi

print_info "Done!"

