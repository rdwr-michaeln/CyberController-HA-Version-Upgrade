import os
import time
from ha_functions import (
    login, break_ha, ha_status, get_router_id, get_net_element_names, 
    get_po_names, establish_ha, version_update, update_status,
    download_df_config, upload_df_config, session,
    wait_for_ha_disable, wait_for_version_update, wait_for_ha_healthy,
    disable_protected_objects, update_network_elements_router_id
)

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

def phase_1_disable_ha(config):
    """Phase 1: Disable HA on primary controller"""
    print("\n=== Phase 1: Disabling HA ===")
    
    # Login to primary and break HA
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    break_ha(config['base_url_primary'])
    wait_for_ha_disable(config['base_url_primary'])

def phase_2_update_secondary(config):
    """Phase 2: Update secondary controller"""
    print("\n=== Phase 2: Updating Secondary Controller ===")
    
    # Login to secondary and perform update
    if not login(config['base_url_secondary'], config['secondary_username'], config['secondary_password']):
        raise Exception("Failed to login to secondary controller")
    
    time.sleep(2)
    if not version_update(config['base_url_secondary'], config['upgrade_file'], config['file_size']):
        raise Exception("Failed to update secondary server")
    
    wait_for_version_update(config['base_url_secondary'], config['secondary_username'], config['secondary_password'])

def phase_3_migrate_config_to_secondary(config):
    """Phase 3: Export config from primary and import to secondary"""
    print("\n=== Phase 3: Migrating Configuration to Secondary ===")
    
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
    return df_config_filename

def phase_4_update_primary(config):
    """Phase 4: Update primary controller"""
    print("\n=== Phase 4: Updating Primary Controller ===")
    
    # Login to primary and perform update
    if not login(config['base_url_primary'], config['primary_username'], config['primary_password']):
        raise Exception("Failed to login to primary controller")
    
    if not version_update(config['base_url_primary'], config['upgrade_file'], config['file_size']):
        raise Exception("Failed to update primary server")
    
    wait_for_version_update(config['base_url_primary'], config['primary_username'], config['primary_password'])

def phase_5_migrate_config_to_primary(config):
    """Phase 5: Export config from secondary and import to primary"""
    print("\n=== Phase 5: Migrating Configuration to Primary ===")
    
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

def phase_6_configure_secondary_router_id(config):
    """Phase 6: Configure router ID on secondary"""
    print("\n=== Phase 6: Configuring Secondary Router ID ===")
    
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

def phase_7_establish_ha(config):
    """Phase 7: Re-establish HA"""
    print("\n=== Phase 7: Re-establishing HA ===")
    
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

def main():
    """Main automation workflow"""
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
        
        # Execute phases in order
        phase_1_disable_ha(config)
        phase_2_update_secondary(config)
        phase_3_migrate_config_to_secondary(config)
        phase_4_update_primary(config)
        phase_5_migrate_config_to_primary(config)
        phase_6_configure_secondary_router_id(config)
        phase_7_establish_ha(config)
        
        print("\n=== HA Automation Completed Successfully! ===")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("HA automation failed. Please check the logs and try again.")
        return False
    
    return True

if __name__ == "__main__":
    main()