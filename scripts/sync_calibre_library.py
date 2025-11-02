#!/usr/bin/env python3
"""
Sync Calibre Library to Remote Server
Alternative Python version with better progress reporting
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Configuration
DEFAULT_REMOTE_HOST = "root@31.97.70.110"
DEFAULT_REMOTE_PATH = "/opt/calibre-library"
DEFAULT_LOCAL_PATH = "./calibre-library"
DEFAULT_SSH_PORT = 22


def print_info(msg):
    print(f"\033[0;32m[INFO]\033[0m {msg}")


def print_warn(msg):
    print(f"\033[1;33m[WARN]\033[0m {msg}")


def print_error(msg):
    print(f"\033[0;31m[ERROR]\033[0m {msg}")


def check_local_library(local_path):
    """Check if local library exists"""
    if not os.path.exists(local_path):
        print_error(f"Local Calibre library not found at: {local_path}")
        sys.exit(1)
    
    if not os.path.isdir(local_path):
        print_error(f"Local path is not a directory: {local_path}")
        sys.exit(1)


def test_ssh_connection(remote_host, ssh_port):
    """Test SSH connection"""
    print_info(f"Testing SSH connection to {remote_host}...")
    try:
        result = subprocess.run(
            ["ssh", "-p", str(ssh_port), "-o", "ConnectTimeout=5", 
             "-o", "BatchMode=yes", remote_host, "exit"],
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            print_warn("SSH connection test failed. Make sure:")
            print_warn("  1. SSH key is set up: ssh-keygen -t rsa")
            print_warn(f"  2. SSH key is added: ssh-copy-id {remote_host}")
            print_warn(f"  3. You can connect: ssh -p {ssh_port} {remote_host}")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
    except subprocess.TimeoutExpired:
        print_error("SSH connection timed out")
        sys.exit(1)
    except FileNotFoundError:
        print_error("SSH command not found. Please install OpenSSH")
        sys.exit(1)


def ensure_remote_directory(remote_host, remote_path, ssh_port):
    """Create remote directory if it doesn't exist"""
    print_info(f"Ensuring remote directory exists: {remote_path}")
    subprocess.run(
        ["ssh", "-p", str(ssh_port), remote_host, 
         f"mkdir -p {remote_path} && chmod 755 {remote_path}"],
        check=True
    )


def sync_library(local_path, remote_host, remote_path, ssh_port, dry_run=False):
    """Sync library using rsync"""
    print_info(f"Syncing Calibre library to {remote_host}:{remote_path}")
    if dry_run:
        print_info("DRY RUN - No files will be transferred")
    
    # Build rsync command
    rsync_args = [
        "rsync",
        "-avz",
        "--progress",
        "-e", f"ssh -p {ssh_port}",
        "--exclude=*.tmp",
        "--exclude=*.bak",
        "--exclude=.DS_Store",
        "--exclude=Thumbs.db",
        "--delete",
    ]
    
    if dry_run:
        rsync_args.append("--dry-run")
    
    rsync_args.extend([
        f"{local_path}/",
        f"{remote_host}:{remote_path}/"
    ])
    
    print_info("Starting sync (this may take a while)...")
    try:
        result = subprocess.run(rsync_args, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_error(f"Sync failed: {e}")
        return False
    except FileNotFoundError:
        print_error("rsync not found. Please install rsync:")
        print_error("  macOS: brew install rsync")
        print_error("  Linux: sudo apt-get install rsync")
        sys.exit(1)


def show_library_stats(remote_host, remote_path, ssh_port):
    """Show library statistics on remote server"""
    print_info("Library statistics:")
    try:
        subprocess.run(
            ["ssh", "-p", str(ssh_port), remote_host,
             f"du -sh {remote_path} && echo 'Files:' && find {remote_path} -type f | wc -l"],
            check=True
        )
    except subprocess.CalledProcessError:
        print_warn("Could not retrieve library statistics")


def restart_docker_containers(remote_host, remote_path, ssh_port):
    """Optional: Restart Docker containers"""
    response = input("Restart Docker containers on server? (y/n): ")
    if response.lower() != 'y':
        return
    
    # Try common Docker paths
    docker_paths = [
        "/opt/calibre-web-clone",
        "/root/calibre-web-clone",
        "/home/calibre/calibre-web-clone",
    ]
    
    print_info("Attempting to restart Docker containers...")
    for path in docker_paths:
        try:
            result = subprocess.run(
                ["ssh", "-p", str(ssh_port), remote_host,
                 f"cd {path} && docker-compose restart backend"],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                print_info(f"Containers restarted from {path}")
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    
    print_warn("Could not restart Docker containers automatically")
    print_warn(f"Please restart manually: ssh {remote_host} 'cd /path/to/app && docker-compose restart'")


def main():
    parser = argparse.ArgumentParser(
        description="Sync Calibre Library to Remote Server"
    )
    parser.add_argument(
        "--remote-host",
        default=DEFAULT_REMOTE_HOST,
        help=f"Remote SSH host (default: {DEFAULT_REMOTE_HOST})"
    )
    parser.add_argument(
        "--remote-path",
        default=DEFAULT_REMOTE_PATH,
        help=f"Remote path for library (default: {DEFAULT_REMOTE_PATH})"
    )
    parser.add_argument(
        "--local-path",
        default=DEFAULT_LOCAL_PATH,
        help=f"Local library path (default: {DEFAULT_LOCAL_PATH})"
    )
    parser.add_argument(
        "--ssh-port",
        type=int,
        default=DEFAULT_SSH_PORT,
        help=f"SSH port (default: {DEFAULT_SSH_PORT})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually syncing"
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Skip Docker container restart prompt"
    )
    
    args = parser.parse_args()
    
    # Convert relative paths to absolute
    local_path = os.path.abspath(args.local_path)
    
    # Validation
    check_local_library(local_path)
    test_ssh_connection(args.remote_host, args.ssh_port)
    
    # Setup
    ensure_remote_directory(args.remote_host, args.remote_path, args.ssh_port)
    
    # Sync
    success = sync_library(
        local_path, 
        args.remote_host, 
        args.remote_path, 
        args.ssh_port,
        dry_run=args.dry_run
    )
    
    if success:
        print_info("Sync completed successfully!")
        print_info(f"Library synced to: {args.remote_host}:{args.remote_path}")
        
        if not args.dry_run:
            show_library_stats(args.remote_host, args.remote_path, args.ssh_port)
            
            if not args.no_restart:
                restart_docker_containers(args.remote_host, args.remote_path, args.ssh_port)
        
        print_info("Done!")
    else:
        print_error("Sync failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

