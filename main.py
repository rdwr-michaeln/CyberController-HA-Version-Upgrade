import os
import time
import json
from datetime import datetime, timezone
from ha_functions import (
    login, break_ha, ha_status, get_router_id, get_net_element_names, 
    get_po_names, establish_ha, version_update, update_status,
    download_df_config, upload_df_config, session,
    wait_for_ha_disable, wait_for_version_update, wait_for_ha_healthy,
    disable_protected_objects, update_network_elements_router_id, get_license
)

# Simple checkpoint functions
def save_progress(phase, status, data=None):
    """Save progress to a simple checkpoint file"""
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
        print(f"⚠️  Could not save progress: {e}")

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
            print(f"⚠️  Could not archive checkpoint: {e}")

def get_user_inputs():
    """Collect all user inputs at the start"""
    print("=== HA Automation Setup ===")
    primary_address = input("Enter Primary Cyber-Controller address: ")
    primary_username = input("Enter Primary username: ")
    primary_password = input("Enter Primary password: ")
    secondary_address = input("Enter Secondary Cyber-Controller address: ")
    secondary_username = input("Enter Secondary username: ")
    secondary_password = input("Enter Secondary password: ")
    upgrade_file = input("Please provide update file .gz: ")
    
    # Validate file exists
    if not os.path.exists(upgrade_file):
        raise FileNotFoundError(f"Upgrade file not found: {upgrade_file}")
    
    return {
        'primary_address': primary_address,
        'primary_username': primary_username,
        'primary_password': primary_password,
        'secondary_address': secondary_address,
        'secondary_username': secondary_username,
        'secondary_password': secondary_password,
        'upgrade_file': upgrade_file,
        'file_size': os.path.getsize(upgrade_file)
    }

def check_license_validity(config):
    """Check license validity on primary controller only"""
    print("\n=== Checking License Validity ===")
    
    # Check primary controller license only
    print("Checking license on primary controller...")
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller for license check")
    
    primary_license_valid = get_license(config['base_url_primary'])
    
    # Only primary controller license is required for configuration migration
    if primary_license_valid:
        print("✅ Valid Cyber Controller Plus License found on primary controller")
        print("Configuration migration will be performed during upgrade")
        return True
    else:
        print("⚠️  Invalid or missing Cyber Controller Plus License detected on primary controller")
        print("Configuration migration will be SKIPPED during upgrade")
        return False

def phase_1_disable_ha(config):
    """Phase 1: Disable HA on primary controller"""
    print("\n=== Phase 1: Disabling HA ===")
    save_progress(1, 'starting')
    
    # Login to primary and break HA
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    break_ha(config['base_url_primary'])
    wait_for_ha_disable(config['base_url_primary'])
    
    save_progress(1, 'completed', {'ha_disabled_at': datetime.now(timezone.utc).isoformat()})

def phase_2_update_secondary(config):
    """Phase 2: Update secondary controller"""
    print("\n=== Phase 2: Updating Secondary Controller ===")
    save_progress(2, 'starting')
    
    # Login to secondary and perform update
    if not login(config['base_url_secondary'], config['secondary_username'], config['secondary_password']):
        raise Exception("Failed to login to secondary controller")
    
    time.sleep(2)
    if not version_update(config['base_url_secondary'], config['upgrade_file'], config['file_size']):
        raise Exception("Failed to update secondary server")
    
    wait_for_version_update(config['base_url_secondary'], config['secondary_username'], config['secondary_password'])
    
    save_progress(2, 'completed', {'secondary_updated_at': datetime.now(timezone.utc).isoformat()})

def phase_3_migrate_config_to_secondary(config):
    """Phase 3: Export config from primary and import to secondary"""
    print("\n=== Phase 3: Migrating Configuration to Secondary ===")
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
    print("\n=== Phase 4: Updating Primary Controller ===")
    save_progress(4, 'starting')
    
    # Login to primary and perform update
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    if not version_update(config['base_url_primary'], config['upgrade_file'], config['file_size']):
        raise Exception("Failed to update primary server")
    
    wait_for_version_update(config['base_url_primary'], config['primary_username'], config['primary_password'])
    
    save_progress(4, 'completed', {'primary_updated_at': datetime.now(timezone.utc).isoformat()})

def phase_5_migrate_config_to_primary(config):
    """Phase 5: Export config from secondary and import to primary"""
    print("\n=== Phase 5: Migrating Configuration to Primary ===")
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
    print("\n=== Phase 6: Configuring Secondary Router ID ===")
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
    print("\n=== Phase 7: Re-establishing HA ===")
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

def main():
    """Main automation workflow with basic checkpoint support"""
    print("🚀 Radware Cyber Controller HA Version Upgrade Automation")
    print("=" * 65)
    
    # Check for existing progress
    progress = load_progress()
    if progress:
        print(f"\n📋 Found previous session from {progress['timestamp']}")
        print(f"Last completed: Phase {progress['phase']} - {progress['status']}")
        resume = input("Do you want to start fresh? (y/n): ").lower().strip()
        if resume in ['n', 'no']:
            print("💡 To resume from a specific point, check manual_recovery_guide.md")
            print("⚠️  Note: This version saves progress but doesn't auto-resume")
    
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
        
        # Check license validity first
        license_valid = check_license_validity(config)
        
        # Execute phases in order
        phase_1_disable_ha(config)
        phase_2_update_secondary(config)
        
        # Only migrate configuration if license is valid
        if license_valid:
            phase_3_migrate_config_to_secondary(config)
        else:
            print("\n=== Phase 3: SKIPPED - Configuration Migration to Secondary ===")
            print("Skipping configuration migration due to invalid/missing license")
            save_progress(3, 'skipped', {'reason': 'Invalid license'})
        
        phase_4_update_primary(config)
        
        # Only migrate configuration if license is valid
        if license_valid:
            phase_5_migrate_config_to_primary(config)
        else:
            print("\n=== Phase 5: SKIPPED - Configuration Migration to Primary ===")
            print("Skipping configuration migration due to invalid/missing license")
            save_progress(5, 'skipped', {'reason': 'Invalid license'})
        
        phase_6_configure_secondary_router_id(config)
        phase_7_establish_ha(config)
        
        print("\n🎉 All phases completed successfully!")
        print("✅ HA upgrade automation finished")
        if not license_valid:
            print("⚠️  Note: Configuration migration was skipped due to license issues")
        
        # Archive the completed checkpoint
        archive_checkpoint()
        
    except KeyboardInterrupt:
        print("\n⏸️  Script interrupted by user (Ctrl+C)")
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
