import requests
import os
import time
import urllib3

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
    if r.status_code != 200:
        print("Break HA Failed")
    else:
        print("HA going to Disable state")

def ha_status(base_url):
    try:
        url = f"{base_url}/mgmt/cybercontroller/ha/status"
        r = session.get(url, verify=False)
        if r.status_code != 200:
            #print("Waiting for Cyber-Controller to became Active")
            return None
        else:
            print("HA is still enabled, waiting for it to be disabled...")
        
        # Check if response has content before parsing JSON
        if not r.text.strip():
            print("Empty response received")
            return None
            
        return r.json()
        
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response text: {r.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
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
    
    print(f"Starting file upload to {url}...")
    print(f"File: {upgrade_file}")
    print(f"File size: {bytes_size} bytes ({bytes_size / (1024*1024):.2f} MB)")
    print("Waiting for file upload to complete...")
    
    try:
        with open(upgrade_file, 'rb') as f:
            files = {
                'Filedata': (upgrade_file, f, 'application/octet-stream')
            }
            # Use session instead of requests and add proper timeout
            response = session.post(url, files=files, verify=False, timeout=1800)
            
        if response.status_code != 200:
            print(f"Version update failed with status code: {response.status_code}")
            print(f"Response text: {response.text}")
            return False
        else:
            print("Version update file uploaded successfully")
            
            # Wait a bit before committing to ensure server has processed the upload
            print("Waiting for server to process the uploaded file...")
            time.sleep(5)
            
            commit_url = f"{base_url}/mgmt/system/config/action/software?type=full"
            commit_response = session.put(commit_url, verify=False, timeout=300)
            
            if commit_response.status_code != 200:
                print(f"Commit version update failed with status code: {commit_response.status_code}")
                print(f"Commit response text: {commit_response.text}")
                return False
            else:   
                print("Starting Update ...")
                return True
                
    except requests.exceptions.Timeout:
        print("Upload timed out - file may be too large or connection too slow")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error during upload: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Upload failed with error: {e}")
        return False
    except FileNotFoundError:
        print(f"Upgrade file not found: {upgrade_file}")
        return False
    except Exception as e:
        print(f"Unexpected error during upload: {e}")
        return False          


def update_status(base_url):
    try:
        url = f"{base_url}/mgmt/system/config/item/settingsbaseparams"
        response = session.get(url, verify=False)
        
        if response.status_code != 200:
            return None
        else:
            print("Updating.....")
        
        # Check if response has content before parsing JSON
        if not response.text.strip():
            print("Empty response received")
            return None
            
        return response.json()
        
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print("Rebooting Cyber-Controller.....")
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
    """Wait for HA to be disabled"""
    print("Waiting for HA to be disabled...")
    ha = True
    while ha:
        ha_result = ha_status(base_url_primary)
        
        # Handle case where ha_status returns None due to error
        if ha_result is None:
            print("Failed to get HA status, waiting to became Active, retrying in 40 seconds...")
            time.sleep(40)
            continue
            
        if ha_result.get('haStatus') == 'disabled':
            ha = False
            print("HA is now disabled!")
        else:
            time.sleep(10)

def wait_for_version_update(base_url, username, password):
    """Wait for version update to complete"""
    ver_update = True
    version = update_status(base_url)
    current_version = version.get('software_version') if version else None

    while ver_update:
        update_result = update_status(base_url)
        
        # Handle case where update_status returns None due to error
        if update_result is None:
            print("Server not ready yet")
            time.sleep(40)
            # Try to login, if it fails, wait and retry the whole loop
            if not login(base_url, username, password):
                print("Server not ready yet")
                time.sleep(20)
            continue
            
        if (update_result.get('lastUpgradeStatus') == 'OK' and 
            update_result.get('software_version') != current_version):
            ver_update = False
            print("Version update completed successfully!")
        else:
            print("Waiting for version update to complete...")
            time.sleep(20)

def wait_for_ha_healthy(base_url_primary):
    """Wait for HA to be healthy on both nodes"""
    print("Waiting for HA to be healthy...")
    ha = True
    while ha:
        ha_result = ha_status(base_url_primary)
        
        # Handle case where ha_status returns None due to error
        if ha_result is None:
            print("Failed to get HA status, retrying in 10 seconds...")
            time.sleep(10)
            continue
            
        if (ha_result.get("primaryHealth") == 'healthy' and 
            ha_result.get("secondaryHealth") == 'healthy'):
            ha = False
            print("HA is healthy on both nodes!")
        else:
            print("HA is not healthy yet, waiting...")
            time.sleep(10)

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
