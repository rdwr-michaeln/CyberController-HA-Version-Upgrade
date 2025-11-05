#!/usr/bin/env python3
"""
Radware CyberController HA Version Upgrade Automation
====================================================
Automated HA upgrade workflow with checkpoint support and configuration migration.
"""

import os
import time
import json
from datetime import datetime, timezone

# Import all required functions from ha_functions.py
from ha_functions import (
    login, break_ha, ha_status, get_router_id, 
    establish_ha, version_update, version_update_chunked, download_df_config, upload_df_config,
    wait_for_ha_disable, wait_for_version_update, wait_for_ha_healthy,
    disable_protected_objects, update_network_elements_router_id, get_license
)

# ========================================
# Checkpoint Management Functions
# ========================================

def save_progress(phase, status, data=None):
    """Save progress to checkpoint file"""
    checkpoint = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'phase': phase,
        'status': status,
        'data': data or {}
    }
    
    try:
        with open('checkpoint.json', 'w') as f:
            json.dump(checkpoint, f, indent=2)
        print(f"💾 Progress saved: Phase {phase} - {status}")
    except Exception as e:
        print(f"⚠️ Could not save progress: {e}")

def load_progress():
    """Load progress from checkpoint file"""
    try:
        if os.path.exists('checkpoint.json'):
            with open('checkpoint.json', 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None

def archive_checkpoint():
    """Archive completed checkpoint"""
    if os.path.exists('checkpoint.json'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f'checkpoint_completed_{timestamp}.json'
        try:
            os.rename('checkpoint.json', archive_name)
            print(f"📁 Checkpoint archived as: {archive_name}")
        except Exception as e:
            print(f"⚠️ Could not archive checkpoint: {e}")


# ========================================
# User Input and Configuration
# ========================================

def get_user_inputs():
    """Collect all user inputs at the start"""
    print("🚀 HA Automation Setup")
    print("=" * 25)
    
    # Primary CyberController Configuration
    primary_address = input("Primary CyberController address: ")
    primary_username = input("Primary username: ")
    primary_password = input("Primary password: ")
    
    # Secondary CyberController Configuration  
    secondary_address = input("Secondary CyberController address: ")
    secondary_username = input("Secondary username: ")
    secondary_password = input("Secondary password: ")
    
    # Upgrade File
    upgrade_file = input("Upgrade file path (.tar.gz): ")
    
    # Validate file exists
    if not os.path.exists(upgrade_file):
        raise FileNotFoundError(f"Upgrade file not found: {upgrade_file}")
    
    file_size = os.path.getsize(upgrade_file)
    
    # Display file information
    print(f"\n📤 Upload Configuration")
    print("=" * 30)
    print(f"File size: {file_size / (1024*1024):.2f} MB ({file_size / (1024*1024*1024):.2f} GB)")
    print(f"Method: Chunked upload with keep-alive")
    
    # Check if requests-toolbelt is available
    try:
        from requests_toolbelt.multipart.encoder import MultipartEncoder
        print("✅ requests-toolbelt available - optimal performance")
    except ImportError:
        print("⚠️  requests-toolbelt not found - will use fallback method")
        print("💡 For better performance, install it with: pip install requests-toolbelt")
    
    # Warn about large files
    if file_size > 5 * 1024 * 1024 * 1024:  # 5GB
        print(f"\n⚠️  Large File Warning")
        print(f"This file is {file_size / (1024*1024*1024):.2f} GB")
        print(f"Upload may take 30+ minutes per controller")
        print(f"Ensure stable network connection and sufficient disk space")
    
    # Always use chunked upload
    upload_method = 'chunked'
    
    # Final confirmation for large files
    if file_size > 5 * 1024 * 1024 * 1024:  # 5GB
        confirm = input(f"\nProceed with {file_size / (1024*1024*1024):.2f} GB file upload? (y/n): ").lower().strip()
        if confirm not in ['y', 'yes']:
            raise KeyboardInterrupt("Upload cancelled by user")
    
    return {
        'primary_address': primary_address,
        'primary_username': primary_username,
        'primary_password': primary_password,
        'secondary_address': secondary_address,
        'secondary_username': secondary_username,
        'secondary_password': secondary_password,
        'upgrade_file': upgrade_file,
        'file_size': file_size,
        'upload_method': upload_method
    }

def perform_version_update(base_url, config, controller_type="controller"):
    """Perform version update using chunked upload with keep-alive"""
    # Determine credentials based on controller type
    if "secondary" in controller_type.lower():
        username = config.get('secondary_username')
        password = config.get('secondary_password')
    else:
        username = config.get('primary_username') 
        password = config.get('primary_password')
    
    print(f"🔄 Using chunked upload with keep-alive for {controller_type}")
    return version_update_chunked(base_url, config['upgrade_file'], config['file_size'],
                                username, password)

def check_license_validity(config):
    """Check license validity on primary controller"""
    print("\n🔍 Checking License Validity")
    print("-" * 30)
    
    print("Checking license on primary controller...")
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller for license check")
    
    primary_license_valid = get_license(config['base_url_primary'])
    
    if primary_license_valid:
        print("✅ Valid CyberController Plus License found")
        print("Configuration migration will be performed during upgrade")
        return True
    else:
        print("⚠️ Invalid or missing CyberController Plus License")
        print("Configuration migration will be SKIPPED during upgrade")
        return False


# ========================================
# Phase Execution Functions
# ========================================

def phase_1_disable_ha(config):
    """Phase 1: Disable HA on primary controller"""
    print("\n📋 Phase 1: Disabling HA")
    print("-" * 25)
    save_progress(1, 'starting')
    
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    break_ha(config['base_url_primary'])
    wait_for_ha_disable(config['base_url_primary'])
    
    save_progress(1, 'completed', {'ha_disabled_at': datetime.now(timezone.utc).isoformat()})

def phase_2_update_secondary(config):
    """Phase 2: Update secondary controller"""
    print("\n📋 Phase 2: Updating Secondary Controller")
    print("-" * 42)
    save_progress(2, 'starting')
    
    if not login(config['base_url_secondary'], config['secondary_username'], config['secondary_password']):
        raise Exception("Failed to login to secondary controller")
    
    time.sleep(2)
    if not perform_version_update(config['base_url_secondary'], config, "secondary controller"):
        raise Exception("Failed to update secondary server")
    
    wait_for_version_update(config['base_url_secondary'], config['secondary_username'], config['secondary_password'])
    
    save_progress(2, 'completed', {'secondary_updated_at': datetime.now(timezone.utc).isoformat()})

def phase_3_migrate_config_to_secondary(config):
    """Phase 3: Export config from primary and import to secondary"""
    print("\n📋 Phase 3: Migrating Configuration to Secondary")
    print("-" * 48)
    save_progress(3, 'starting')
    
    # Export config from primary
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    time.sleep(5)
    df_config_filename = download_df_config(config['base_url_primary'])
    if df_config_filename is None:
        raise Exception("Failed to download DefenseFlow configuration from primary")
    
    # Import config to secondary
    if not login(config['base_url_secondary'], config['secondary_username'], config['secondary_password']):
        raise Exception("Failed to login to secondary controller")
    
    time.sleep(5)
    upload_df_config(df_config_filename, config['base_url_secondary'])
    
    save_progress(3, 'completed', {
        'config_filename': df_config_filename,
        'migrated_at': datetime.now(timezone.utc).isoformat()
    })
    return df_config_filename

def phase_4_update_primary(config):
    """Phase 4: Update primary controller"""
    print("\n📋 Phase 4: Updating Primary Controller")
    print("-" * 40)
    save_progress(4, 'starting')
    
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    if not perform_version_update(config['base_url_primary'], config, "primary controller"):
        raise Exception("Failed to update primary server")
    
    wait_for_version_update(config['base_url_primary'], config['primary_username'], config['primary_password'])
    
    save_progress(4, 'completed', {'primary_updated_at': datetime.now(timezone.utc).isoformat()})

def phase_5_migrate_config_to_primary(config):
    """Phase 5: Export config from secondary and import to primary"""
    print("\n📋 Phase 5: Migrating Configuration to Primary")
    print("-" * 46)
    save_progress(5, 'starting')
    
    # Export config from secondary
    if not login(config['base_url_secondary'], config['secondary_username'], config['secondary_password']):
        raise Exception("Failed to login to secondary controller")
    
    df_config_filename = download_df_config(config['base_url_secondary'])
    if df_config_filename is None:
        raise Exception("Failed to download DefenseFlow configuration from secondary")
    
    # Import config to primary
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    time.sleep(5)
    upload_df_config(df_config_filename, config['base_url_primary'])
    
    save_progress(5, 'completed', {
        'config_filename': df_config_filename,
        'migrated_at': datetime.now(timezone.utc).isoformat()
    })

def phase_6_configure_secondary_router_id(config):
    """Phase 6: Configure router ID on secondary"""
    print("\n📋 Phase 6: Configuring Secondary Router ID")
    print("-" * 44)
    save_progress(6, 'starting')
    
    if not login(config['base_url_secondary'], config['secondary_username'], config['secondary_password']):
        raise Exception("Failed to login to secondary controller")
    
    # Get router ID and update network elements
    secondary_router_id = get_router_id(config['base_url_secondary'])
    if not secondary_router_id:
        raise Exception("Failed to get router ID from secondary")
    
    print(f"Changing router ID on secondary to: {secondary_router_id}")
    
    # Disable protected objects
    disable_protected_objects(config['base_url_secondary'])
    
    # Update network elements with router ID
    update_network_elements_router_id(config['base_url_secondary'], secondary_router_id)
    
    save_progress(6, 'completed', {
        'router_id': secondary_router_id,
        'configured_at': datetime.now(timezone.utc).isoformat()
    })

def phase_7_establish_ha(config):
    """Phase 7: Re-establish HA"""
    print("\n📋 Phase 7: Re-establishing HA")
    print("-" * 30)
    save_progress(7, 'starting')
    
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    print("Establishing HA...")
    establish_ha(
        config['primary_address'], 
        config['secondary_address'], 
        config['secondary_username'], 
        config['secondary_password'], 
        config['base_url_primary']
    )
    
    wait_for_ha_healthy(config['base_url_primary'])
    
    save_progress(7, 'completed', {
        'ha_established_at': datetime.now(timezone.utc).isoformat(),
        'ha_healthy': True
    })


# ========================================
# Main Workflow Function
# ========================================

def main():
    """Main automation workflow with checkpoint support"""
    print("🚀 Radware CyberController HA Version Upgrade Automation")
    print("=" * 58)
    
    # Check for existing progress
    progress = load_progress()
    start_phase = 1
    if progress:
        print(f"\n📋 Found previous session from {progress['timestamp']}")
        print(f"Last completed: Phase {progress['phase']} - {progress['status']}")
        resume = input("Do you want to start fresh? (y/n): ").lower().strip()
        if resume in ['n', 'no']:
            # Handle phase as either string or int, and handle error states
            phase_num = progress['phase']
            if isinstance(phase_num, str):
                if phase_num == 'error':
                    print("⚠️ Previous run had an error. Starting from Phase 1.")
                    start_phase = 1
                else:
                    try:
                        phase_num = int(phase_num)
                    except ValueError:
                        print("⚠️ Invalid phase in checkpoint. Starting from Phase 1.")
                        start_phase = 1
                        phase_num = 1
            
            if isinstance(phase_num, int):
                if progress['status'] == 'completed':
                    start_phase = phase_num + 1
                    print(f"🔄 Resuming from Phase {start_phase}")
                else:
                    start_phase = phase_num
                    print(f"🔄 Resuming Phase {start_phase}")
    
    try:
        # Get user inputs
        inputs = get_user_inputs()
        
        # Create configuration object
        config = {
            **inputs,
            'base_url_primary': f"https://{inputs['primary_address']}",
            'base_url_secondary': f"https://{inputs['secondary_address']}"
        }
        
        print(f"\nStarting HA automation process...")
        print(f"Primary: {config['primary_address']}")
        print(f"Secondary: {config['secondary_address']}")
        print(f"Upgrade file: {config['upgrade_file']} ({config['file_size'] / (1024*1024):.2f} MB)")
        print(f"Upload method: Chunked (with progress tracking and keep-alive)")
        
        # Check license validity first
        license_valid = check_license_validity(config)
        
        # Execute phases based on start_phase
        if start_phase <= 1:
            phase_1_disable_ha(config)
        else:
            print("⏭️ Skipping Phase 1 (already completed)")
            
        if start_phase <= 2:
            phase_2_update_secondary(config)
        else:
            print("⏭️ Skipping Phase 2 (already completed)")
        
        # Only migrate configuration if license is valid
        if start_phase <= 3:
            if license_valid:
                phase_3_migrate_config_to_secondary(config)
            else:
                print("\n📋 Phase 3: SKIPPED - Configuration Migration to Secondary")
                print("Skipping configuration migration due to invalid/missing license")
                save_progress(3, 'skipped', {'reason': 'Invalid license'})
        else:
            print("⏭️ Skipping Phase 3 (already completed)")
        
        if start_phase <= 4:
            phase_4_update_primary(config)
        else:
            print("⏭️ Skipping Phase 4 (already completed)")
        
        # Only migrate configuration if license is valid
        if start_phase <= 5:
            if license_valid:
                phase_5_migrate_config_to_primary(config)
            else:
                print("\n📋 Phase 5: SKIPPED - Configuration Migration to Primary")
                print("Skipping configuration migration due to invalid/missing license")
                save_progress(5, 'skipped', {'reason': 'Invalid license'})
        else:
            print("⏭️ Skipping Phase 5 (already completed)")
        
        if start_phase <= 6:
            phase_6_configure_secondary_router_id(config)
        else:
            print("⏭️ Skipping Phase 6 (already completed)")
            
        if start_phase <= 7:
            phase_7_establish_ha(config)
        else:
            print("⏭️ Skipping Phase 7 (already completed)")
        
        print("\n🎉 All phases completed successfully!")
        print("✅ HA upgrade automation finished")
        if not license_valid:
            print("⚠️ Note: Configuration migration was skipped due to license issues")
        
        # Archive the completed checkpoint
        archive_checkpoint()
        
    except KeyboardInterrupt:
        print("\n⏸️ Script interrupted by user (Ctrl+C)")
        print("💾 Progress has been saved to checkpoint.json")
        print("📊 Check manual_recovery_guide.md for recovery procedures")
        return False
        
    except Exception as e:
        print(f"\n💥 Script failed with error: {e}")
        save_progress('error', 'failed', {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()})
        print("💾 Error details saved to checkpoint.json")
        print("📊 Check manual_recovery_guide.md for recovery procedures")
        return False
    
    return True

if __name__ == "__main__":
    main()
