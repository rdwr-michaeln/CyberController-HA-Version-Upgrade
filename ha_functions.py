import requests
import os
import time
import urllib3
from datetime import datetime, timezone

# Disable SSL certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global session object
session = requests.Session()

def login(base_url, username, password):
    try:
        url = f"{base_url}/mgmt/system/user/login"
        payload = {"username": username, "password": password}
        r = session.post(url, json=payload, verify=False)
        if r.status_code != 200:
            return False
        else:
            print("Login successful")
            return True
    except requests.exceptions.RequestException as e:
        # Server is not ready yet, return False to indicate login failed
        return False


def break_ha(base_url_primary):
    url = f"{base_url_primary}/mgmt/cybercontroller/ha/config"
    r = session.delete(url, verify=False)
    if r.status_code == 200:
         print("HA going to Disable state")

def ha_status(base_url):
    try:
        url = f"{base_url}/mgmt/cybercontroller/ha/status"
        r = session.get(url, verify=False)
        if r.status_code != 200:
            return None
        
        # Check if response has content before parsing JSON
        if not r.text.strip():
            return None
            
        return r.json()
        
    except requests.exceptions.JSONDecodeError as e:
        print(f"\n📊 JSON decode error: {e}")
        print(f"Response text: {r.text}")
        return None
    except requests.exceptions.RequestException as e:
        return None

def get_router_id(base_url):
    try:
        url = f"{base_url}/mgmt/device/df/config?prop=BGP_ROUTER_ID,BGP_HOLD_TIME,BGP_LOCAL_AS"
        response = session.get(url, verify=False)
        
        if response.status_code != 200:
            print(f"Failed to get router ID. Status code: {response.status_code}")
            return None  
        data = response.json()
        return data.get('BGP_ROUTER_ID')
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    
def get_net_element_names(base_url):
    try:
        url = f"{base_url}/mgmt/device/df/config/NetworkElements?count=100"
        response = session.get(url, verify=False)
        if response.status_code != 200:
            print(f"Failed to get network element names. Status code: {response.status_code}")
            return None  
        data = response.json()
        return [element.get('name') for element in data.get('NetworkElements', []) if 'name' in element]
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

def get_po_names(base_url):
    try:
        url = f"{base_url}/mgmt/v2/device/df/restv2/protected-objects/configure/security-settings/?includeNameSort=false"
        payload = {
        "protectedObjectNames": []
}

        response = session.post(url, json=payload, verify=False)
        if response.status_code != 200:
            print(f"Failed to get protected object names. Status code: {response.status_code}")    
            return None  
        data = response.json()
        return [obj.get("name") for obj in data["protectedObjects"] if "name" in obj]
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    

def establish_ha(primary_address, secondary_address, secondary_username, secondary_password, base_url_primary):
    url = f"{base_url_primary}/mgmt/cybercontroller/ha/config"
    payload = {
    "primaryIP": f"{primary_address}",
    "secondaryIP": f"{secondary_address}",
    "virtualIP": "",
    "autoFailover": True,
    "secondary": {
        "user": f"{secondary_username}",
        "password": f"{secondary_password}"
    }
    }
    r = session.post(url, json=payload, verify=False)
    if r.status_code != 200:
        print("Trying to establish HA")
    else:
        print("Establishing HA...")



def version_update(base_url, upgrade_file, bytes_size):
    url = f"{base_url}/mgmt/system/config/action/software?type=full&filesize={bytes_size}"
    
    print(f"\n🔄 Starting Version Update")
    print(f"{'='*60}")
    print(f"📁 File: {os.path.basename(upgrade_file)}")
    print(f"📊 Size: {bytes_size / (1024*1024):.2f} MB ({bytes_size:,} bytes)")
    print(f"🎯 Target: {base_url.split('//')[1] if '//' in base_url else base_url}")
    print(f"{'='*60}")
    print(f"⬆️  Uploading file... This may take several minutes...")
    
    try:
        with open(upgrade_file, 'rb') as f:
            files = {
                'Filedata': (upgrade_file, f, 'application/octet-stream')
            }
            # Use session instead of requests and add proper timeout
            response = session.post(url, files=files, verify=False, timeout=1800)
            
        if response.status_code != 200:
            print(f"❌ Upload failed with status code: {response.status_code}")
            print(f"📝 Response: {response.text}")
            return False
        else:
            print(f"✅ File uploaded successfully!")
            
            # Wait a bit before committing to ensure server has processed the upload
            print(f"⏳ Processing uploaded file...")
            for i in range(5):
                print(f"   {'▓' * (i + 1)}{'░' * (4 - i)} {i + 1}/5 seconds", end='\r')
                time.sleep(1)
            print("\n")
            
            commit_url = f"{base_url}/mgmt/system/config/action/software?type=full"
            commit_response = session.put(commit_url, verify=False, timeout=300)
            
            if commit_response.status_code != 200:
                print(f"❌ Commit failed with status code: {commit_response.status_code}")
                print(f"📝 Response: {commit_response.text}")
                return False
            else:   
                print(f"🚀 Starting system update...")
                return True
                
    except requests.exceptions.Timeout:
        print("⏰ Upload timed out - file may be too large or connection too slow")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 Connection error during upload: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"🌐 Upload failed with error: {e}")
        return False
    except FileNotFoundError:
        print(f"📂 Upgrade file not found: {upgrade_file}")
        return False
    except Exception as e:
        print(f"💥 Unexpected error during upload: {e}")
        return False          


def update_status(base_url):
    try:
        url = f"{base_url}/mgmt/system/config/item/settingsbaseparams"
        response = session.get(url, verify=False)
        
        if response.status_code != 200:
            return None
        else:
            print("🔄 System updating...", end='', flush=True)
        
        # Check if response has content before parsing JSON
        if not response.text.strip():
            print("\n⚠️  Empty response received")
            return None
            
        return response.json()
        
    except requests.exceptions.JSONDecodeError as e:
        print(f"\n📊 JSON decode error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print("\n🔄 System rebooting...", flush=True)
        return None


def download_df_config(base_url):
    
    print('Exporting DefenseFlow Configuration from Vision')
    url = f"{base_url}/mgmt/device/df/config/getfromdevice?saveToDb=false&type=config"
    response = session.get(url, stream=True)
    
    if response.status_code != 200:
        print(f"Failed to download config file. Status code: {response.status_code}")
        return None
    
    # Open the file in binary write mode and download it in chunks
    if 'Content-Disposition' in response.headers:
        # Extract filename from Content-Disposition
        content_disposition = response.headers['Content-Disposition']
        filename = content_disposition.split('filename=')[-1].strip('"')
    else:
        # If no Content-Disposition header, create a default filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"DefenseFlowConfiguration_{timestamp}.zip"
        print(f"No filename in response, using default: {filename}")
    
    try:
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive new chunks
                    file.write(chunk)

        print(f'Successfully Exported File {filename}')
        return filename
    except Exception as e:
        print(f"Error saving file: {e}")
        return None
   

def upload_df_config(filename, base_url):
    try:
        print('Importing DefenseFlow Configuration to Cyber-Controller Plus')
        url = f"{base_url}/mgmt/device/df/config/sendtodevice?fileName={filename}&type=config"
        files = {'Filedata': ('DefenseFlow-To-CCPlus.code-workspace', open(filename, 'rb'), 'application/octet-stream')}
        r = session.post(url, files=files)
        
        if r.status_code != 200:
            print(f"Error - Cyber-Controller: status code {r.status_code} with message {r.text}")
            exit(1)
        
        # Check if response has content before parsing JSON
        if not r.text.strip():
            print("Empty response received from upload")
            exit(1)
        
        r_dict = r.json()
        if 'status' in r_dict and r_dict['status'] != 'ok':
            print(f"Error - Cyber-Controller: '{r_dict['message']}'")
            exit(1)

        print("Successfully Migrated DefenseFlow Configuration to Cyber-Controller Plus")
        
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error during upload: {e}")
        print(f"Response text: {r.text}")
        exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Request error during upload: {e}")
        exit(1)

# Helper functions for better organization

def wait_for_ha_disable(base_url_primary):
    """Wait for HA to be disabled with progress indication"""
    print("🔄 Waiting for HA to be disabled...")
    ha = True
    check_count = 0
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    start_time = time.time()
    
    while ha:
        check_count += 1
        elapsed_time = int(time.time() - start_time)
        ha_result = ha_status(base_url_primary)
        
        # Handle case where ha_status returns None due to error
        if ha_result is None:
            print(f"\r{spinner[check_count % len(spinner)]} Checking HA status... ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            time.sleep(20)  # Reduced from 40 to 20 seconds for server issues
            continue
            
        if ha_result.get('haStatus') == 'disabled':
            ha = False
            print(f"\n✅ HA is now disabled! (took {elapsed_time//60:02d}:{elapsed_time%60:02d})")
        else:
            current_status = ha_result.get('haStatus', 'unknown')
            print(f"\r{spinner[check_count % len(spinner)]} HA Status: {current_status} - waiting for disable... ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            time.sleep(5)  # Reduced from 10 to 5 seconds for faster response

def wait_for_version_update(base_url, username, password):
    """Wait for version update to complete with elegant progress display"""
    print(f"\n📊 Monitoring Update Progress")
    print(f"{'='*50}")
    
    ver_update = True
    version = update_status(base_url)
    current_version = version.get('software_version') if version else None
    start_time = time.time()
    check_count = 0
    
    # Progress indicators
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    while ver_update:
        check_count += 1
        elapsed_time = int(time.time() - start_time)
        
        update_result = update_status(base_url)
        
        # Handle case where update_status returns None due to error
        if update_result is None:
            print(f"\r{spinner[check_count % len(spinner)]} Server not ready yet... ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            time.sleep(30)  # Reduced from 40 to 30 seconds for server recovery
            # Try to login, if it fails, wait and retry the whole loop
            if not login(base_url, username, password):
                print(f"\r{spinner[check_count % len(spinner)]} Waiting for server to come online... ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
                time.sleep(15)  # Reduced from 20 to 15 seconds
            continue
            
        if (update_result.get('lastUpgradeStatus') == 'OK' and 
            update_result.get('software_version') != current_version):
            ver_update = False
            new_version = update_result.get('software_version', 'Unknown')
            print(f"\n✅ Version update completed successfully!")
            print(f"🎯 New version: {new_version}")
            print(f"⏱️  Total time: {elapsed_time//60:02d}:{elapsed_time%60:02d}")
        else:
            status = update_result.get('lastUpgradeStatus', 'In Progress')
            print(f"\r{spinner[check_count % len(spinner)]} Update in progress... Status: {status} ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            time.sleep(15)  # Reduced from 20 to 15 seconds for more frequent updates

def wait_for_ha_healthy(base_url_primary):
    """Wait for HA to be healthy on both nodes with progress indication"""
    print("🔄 Waiting for HA to be healthy...")
    ha = True
    check_count = 0
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    start_time = time.time()
    
    while ha:
        check_count += 1
        elapsed_time = int(time.time() - start_time)
        ha_result = ha_status(base_url_primary)
        
        # Handle case where ha_status returns None due to error
        if ha_result is None:
            print(f"\r{spinner[check_count % len(spinner)]} Checking HA health status... ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            time.sleep(8)  # Reduced from 10 to 8 seconds
            continue
            
        primary_health = ha_result.get("primaryHealth", "unknown")
        secondary_health = ha_result.get("secondaryHealth", "unknown")
        
        if primary_health == 'healthy' and secondary_health == 'healthy':
            ha = False
            print(f"\n✅ HA is healthy on both nodes! (took {elapsed_time//60:02d}:{elapsed_time%60:02d})")
            print(f"   📊 Primary: {primary_health} | Secondary: {secondary_health}")
        else:
            print(f"\r{spinner[check_count % len(spinner)]} HA Health - Primary: {primary_health} | Secondary: {secondary_health} ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            time.sleep(8)  # Reduced from 10 to 8 seconds

def disable_protected_objects(base_url):
    """Disable all protected objects on the given server"""
    print("Disabling protected objects...")
    data = get_po_names(base_url)
    if not data:
        print("No protected objects found")
        return
        
    for po_name in data:
        url = f"{base_url}/mgmt/v2/device/df/restv2/protected-objects/configure/?action=disable" 
        payload = [po_name]  # Send as a list with the protected object name
        response = session.put(url, json=payload, verify=False)

def update_network_elements_router_id(base_url, router_id):
    """Update router ID for all network elements"""
    print(f"Updating network elements with router ID: {router_id}")
    elements_names = get_net_element_names(base_url)
    if not elements_names:
        print("No network elements found")
        return
        
    for name in elements_names:
        url = f"{base_url}/mgmt/device/df/config/NetworkElements/{name}/"
        payload = {
            "name": f"{name}",
            "RouterID": f"{router_id}"
        }
        response = session.put(url, json=payload, verify=False)
        if response.status_code == 200:
            print(f"Updated router ID for network element: {name}")
        else:
            print(f"Failed to update router ID for network element: {name}")

def get_license(base_url):
    """Get license information from the server and check if Cyber Controller Plus License is valid"""
    today_ms = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    
    try:
        url = f"{base_url}/mgmt/system/config/itemlist/licenseinfo"
        response = session.get(url, verify=False)
        
        if response.status_code != 200:
            print(f"Failed to get license information. Status code: {response.status_code}")
            return False
            
        data = response.json()
        
        # Search for Cyber Controller Plus License in the data
        for group in data:
            for item in group:
                if isinstance(item, dict) and item.get("description") == "Cyber Controller Plus License":
                    exp = item.get("licenseExpirationDate")
                    
                    # If no expiration date, consider it as valid (perpetual license)
                    if exp is None:
                        print("Cyber Controller Plus License found - No expiration date (perpetual)")
                        return True
                    
                    # Check if license has not expired
                    if exp > today_ms:
                        exp_date = datetime.fromtimestamp(exp / 1000, timezone.utc).strftime("%Y-%m-%d")
                        print(f"Cyber Controller Plus License found - Valid until: {exp_date}")
                        return True
                    else:
                        exp_date = datetime.fromtimestamp(exp / 1000, timezone.utc).strftime("%Y-%m-%d")
                        print(f"Cyber Controller Plus License found but EXPIRED on: {exp_date}")
                        return False
        
        # License not found
        print("Cyber Controller Plus License not found")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Request error while checking license: {e}")
        return False
    except Exception as e:
        print(f"Error while processing license data: {e}")
        return False
