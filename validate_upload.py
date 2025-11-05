#!/usr/bin/env python3
"""
Pre-upload Validation Utility
=============================
Run this before starting the main upgrade to validate prerequisites
"""

import os
import sys
import shutil
from ha_functions import validate_upload_prerequisites, login

def main():
    print("🔍 Pre-Upload Validation Utility")
    print("=" * 40)
    
    # Get basic inputs
    server_address = input("Server address: ")
    username = input("Username: ")
    password = input("Password: ")
    upgrade_file = input("Upgrade file path: ")
    
    if not os.path.exists(upgrade_file):
        print(f"❌ File not found: {upgrade_file}")
        return False
    
    file_size = os.path.getsize(upgrade_file)
    base_url = f"https://{server_address}"
    
    print(f"\n📊 File Information:")
    print(f"   File: {upgrade_file}")
    print(f"   Size: {file_size / (1024*1024):.2f} MB ({file_size / (1024*1024*1024):.2f} GB)")
    
    # System checks
    print(f"\n💻 System Checks:")
    
    # Memory check
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        for line in meminfo.split('\n'):
            if 'MemAvailable:' in line:
                mem_available = int(line.split()[1]) * 1024  # Convert KB to bytes
                print(f"   Available Memory: {mem_available / (1024*1024):.2f} MB")
                if mem_available < file_size * 0.1:  # Need at least 10% of file size
                    print(f"   ⚠️  Low memory warning")
                else:
                    print(f"   ✅ Sufficient memory")
                break
    except:
        print(f"   ⚠️  Could not check memory")
    
    # Disk space check
    try:
        free_space = shutil.disk_usage('.').free
        print(f"   Available Disk: {free_space / (1024*1024):.2f} MB")
        if free_space < file_size * 0.2:
            print(f"   ⚠️  Low disk space warning")
        else:
            print(f"   ✅ Sufficient disk space")
    except:
        print(f"   ⚠️  Could not check disk space")
    
    # Network and server checks
    print(f"\n🌐 Network and Server Checks:")
    if validate_upload_prerequisites(base_url, upgrade_file, file_size):
        print(f"   ✅ All prerequisites passed")
    else:
        print(f"   ❌ Prerequisites validation failed")
        return False
    
    # Authentication check
    print(f"\n🔐 Authentication Check:")
    if login(base_url, username, password):
        print(f"   ✅ Login successful")
    else:
        print(f"   ❌ Login failed")
        return False
    
    print(f"\n🎉 All validations passed!")
    print(f"💡 You can now run the main upgrade script with confidence")
    
    # Estimate upload time
    # Rough estimate: 1 Mbps = ~30 minutes for 9GB
    estimated_minutes = (file_size / (1024*1024)) / 4  # Assuming 4 MB/minute average
    print(f"🕐 Estimated upload time per controller: {estimated_minutes:.0f} minutes")
    
    return True

if __name__ == "__main__":
    try:
        if main():
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⏸️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        sys.exit(1)