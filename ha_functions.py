import requests
import os
import time
import urllib3
import ssl
import socket
import threading
import gc
from datetime import datetime, timezone

# Optional import for chunked uploads
try:
    from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
    HAS_CHUNKED_SUPPORT = True
except ImportError:
    HAS_CHUNKED_SUPPORT = False

# Disable SSL certificate warnings and verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global session object with SSL verification disabled
session = requests.Session()
session.verify = False

# Configure session for better connection handling
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up retry strategy
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

# Mount adapter with retry strategy
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Also disable SSL verification globally for the session
try:
    # For older Python versions
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# Global variable to control keep-alive thread
keep_alive_stop = threading.Event()

def send_keep_alive(ip_address, interval=300):
    """
    Send keep-alive requests every interval seconds to maintain session
    """
    while not keep_alive_stop.is_set():
        try:
            # Send a simple GET request to keep session alive - using HA status endpoint
            url = f"https://{ip_address}/mgmt/cybercontroller/ha/status"
            response = session.get(url, timeout=30)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Keep-alive sent - Status: {response.status_code}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Keep-alive failed: {str(e)}")
        
        # Wait for the specified interval or until stop event is set
        keep_alive_stop.wait(interval)

def login(base_url, username, password):
    try:
        url = f"{base_url}/mgmt/system/user/login"
        payload = {"username": username, "password": password}
        r = session.post(url, json=payload, verify=False)
        if r.status_code != 200:
            print(f"❌ Login failed with status code: {r.status_code}")
            if r.text:
                print(f"📝 Response: {r.text}")
            return False
        else:
            print("✅ Login successful")
            return True
    except requests.exceptions.RequestException as e:
        print(f"🔌 Login failed with error: {e}")
        # Server is not ready yet, return False to indicate login failed
        return False

def ensure_authenticated(base_url, username, password):
    """Ensure we have a valid session, re-authenticate if needed"""
    try:
        # Test session with a simple API call
        test_url = f"{base_url}/mgmt/system/status"
        r = session.get(test_url, verify=False, timeout=10)
        if r.status_code == 401:
            print("🔑 Session expired, re-authenticating...")
            return login(base_url, username, password)
        elif r.status_code == 200:
            return True
        else:
            print(f"⚠️  Session test returned status {r.status_code}, re-authenticating...")
            return login(base_url, username, password)
    except requests.exceptions.RequestException:
        print("🔑 Session test failed, re-authenticating...")
        return login(base_url, username, password)


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





def version_update(base_url, upgrade_file, bytes_size, username=None, password=None):
    """
    Enhanced version update with keep-alive for large files
    """
    global keep_alive_stop
    keep_alive_thread = None
    ip_address = base_url.split('//')[1].split('/')[0] if '//' in base_url else base_url.split('/')[0]
    
    # For files > 500MB, start keep-alive thread during upload
    start_keep_alive = bytes_size > 500 * 1024 * 1024  # 500MB threshold
    
    # Regular upload with keep-alive support
    url = f"{base_url}/mgmt/system/config/action/software?type=full&filesize={bytes_size}"
    
    print(f"\n🔄 Starting Version Update")
    print(f"{'='*60}")
    print(f"📁 File: {os.path.basename(upgrade_file)}")
    print(f"📊 Size: {bytes_size / (1024*1024):.2f} MB ({bytes_size:,} bytes)")
    print(f"🎯 Target: {base_url.split('//')[1] if '//' in base_url else base_url}")
    print(f"{'='*60}")
    
    # Retry logic for connection issues
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"🔄 Retry attempt {attempt} of {max_retries - 1}...")
                # Re-authenticate before retry
                if username and password:
                    print("🔑 Re-authenticating before retry...")
                    if not login(base_url, username, password):
                        print("❌ Re-authentication failed")
                        continue
            
            print(f"⬆️  Uploading file... This may take several minutes...")
            
            # Start keep-alive thread for large files
            if start_keep_alive:
                keep_alive_stop.clear()
                keep_alive_thread = threading.Thread(target=send_keep_alive, args=(ip_address, 300))
                keep_alive_thread.daemon = True
                keep_alive_thread.start()
                print("🔄 Keep-alive started (5 minute intervals)")
            
            try:
                # Progress tracking file wrapper
                class ProgressFileReader:
                    def __init__(self, file_path, file_size):
                        self.file = open(file_path, 'rb')
                        self.file_size = file_size
                        self.bytes_read = 0
                        self.last_percent = -1
                        
                    def read(self, size=-1):
                        """Read method that tracks progress"""
                        chunk = self.file.read(size)
                        if chunk:
                            self.bytes_read += len(chunk)
                            
                            # Update progress display
                            percent = int((self.bytes_read / self.file_size) * 100)
                            if percent != self.last_percent and percent % 5 == 0:  # Update every 5%
                                mb_uploaded = self.bytes_read / (1024*1024)
                                total_mb = self.file_size / (1024*1024)
                                print(f"\r   ⬆️  {percent}% - {mb_uploaded:.1f} MB / {total_mb:.1f} MB", end='', flush=True)
                                self.last_percent = percent
                                
                        return chunk
                    
                    def __len__(self):
                        return self.file_size
                        
                    def close(self):
                        self.file.close()
                
                # Use progress file reader
                file_reader = ProgressFileReader(upgrade_file, bytes_size)
                try:
                    files = {
                        'Filedata': (os.path.basename(upgrade_file), file_reader, 'application/octet-stream')
                    }
                    # Enhanced timeout and connection settings
                    response = session.post(url, files=files, verify=False, timeout=3600, 
                                          stream=False)
                    print()  # New line after progress
                finally:
                    file_reader.close()
            finally:
                # Stop keep-alive thread
                if keep_alive_thread:
                    keep_alive_stop.set()
                    print("🛑 Keep-alive stopped")
            
            if response.status_code != 200:
                print(f"❌ Upload failed with status code: {response.status_code}")
                print(f"📝 Response: {response.text}")
                if attempt < max_retries - 1:
                    print(f"⏳ Waiting 30 seconds before retry...")
                    time.sleep(30)
                    continue
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
                
                # If commit fails with 401, try re-authenticating and retry once
                if commit_response.status_code == 401 and username and password:
                    print("🔑 Session expired, re-authenticating...")
                    if login(base_url, username, password):
                        print("🔄 Retrying commit...")
                        commit_response = session.put(commit_url, verify=False, timeout=300)
                
                if commit_response.status_code != 200:
                    print(f"❌ Commit failed with status code: {commit_response.status_code}")
                    print(f"📝 Response: {commit_response.text}")
                    return False
                else:   
                    print(f"🚀 Starting system update...")
                    return True
                    
        except requests.exceptions.Timeout:
            print(f"⏰ Upload timed out on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting 60 seconds before retry...")
                time.sleep(60)
                continue
            else:
                print("❌ Max retries exceeded due to timeouts")
                return False
                
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Connection error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting 30 seconds before retry...")
                time.sleep(30)
                continue
            else:
                print("❌ Max retries exceeded due to connection errors")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"🌐 Request error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting 30 seconds before retry...")
                time.sleep(30)
                continue
            else:
                print("❌ Max retries exceeded due to request errors")
                return False
                
        except FileNotFoundError:
            print(f"📂 Upgrade file not found: {upgrade_file}")
            return False
            
        except Exception as e:
            print(f"💥 Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting 30 seconds before retry...")
                time.sleep(30)
                continue
            else:
                print("❌ Max retries exceeded due to unexpected errors")
                return False
    
    # If we get here, all retries failed
    return False          


def version_update_chunked(base_url, upgrade_file, bytes_size, username=None, password=None):
    """
    Enhanced version update with chunked upload for better memory management
    """
    url = f"{base_url}/mgmt/system/config/action/software?type=full&filesize={bytes_size}"
    
    print(f"\n🔄 Starting Version Update (Chunked Method)")
    print(f"{'='*60}")
    print(f"📁 File: {os.path.basename(upgrade_file)}")
    print(f"📊 Size: {bytes_size / (1024*1024):.2f} MB ({bytes_size:,} bytes)")
    print(f"🎯 Target: {base_url.split('//')[1] if '//' in base_url else base_url}")
    print(f"{'='*60}")
    
    # Check if chunked support is available
    if not HAS_CHUNKED_SUPPORT:
        print("⚠️  requests-toolbelt not found, using fallback chunked method...")
        print("💡 For better performance, install it with: pip install requests-toolbelt")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"\n🔄 Retry attempt {attempt} of {max_retries - 1}...")
                # Re-authenticate before retry
                if username and password:
                    print("🔑 Re-authenticating before retry...")
                    if not login(base_url, username, password):
                        print("❌ Re-authentication failed")
                        continue
            
            print(f"⬆️  Uploading file with chunked method... This may take several minutes...")
            
            if HAS_CHUNKED_SUPPORT:
                # Use requests-toolbelt for optimal chunked upload
                success = _upload_with_toolbelt(url, upgrade_file, bytes_size)
            else:
                # Use fallback chunked method
                success = _upload_with_fallback(url, upgrade_file, bytes_size)
            
            if not success:
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    print(f"⏳ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                return False
            
            print(f"✅ File uploaded successfully!")
            
            # Wait before committing
            print(f"⏳ Processing uploaded file...")
            for i in range(5):
                print(f"   {'▓' * (i + 1)}{'░' * (4 - i)} {i + 1}/5 seconds", end='\r')
                time.sleep(1)
            print("\n")
            
            # Commit the upload
            commit_url = f"{base_url}/mgmt/system/config/action/software?type=full"
            print(f"🔄 Committing upload...")
            commit_response = session.put(commit_url, verify=False, timeout=600)
            
            # Handle session expiration during commit
            if commit_response.status_code == 401 and username and password:
                print("🔑 Session expired during commit, re-authenticating...")
                if login(base_url, username, password):
                    print("🔄 Retrying commit...")
                    commit_response = session.put(commit_url, verify=False, timeout=600)
            
            if commit_response.status_code != 200:
                print(f"❌ Commit failed with status code: {commit_response.status_code}")
                if hasattr(commit_response, 'text') and commit_response.text:
                    print(f"📝 Response: {commit_response.text[:500]}...")
                return False
            
            print(f"🚀 Starting system update...")
            return True
                    
        except requests.exceptions.Timeout as e:
            print(f"\n⏰ Upload timed out on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                wait_time = 60 * (attempt + 1)
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            else:
                print("❌ Max retries exceeded due to timeouts")
                return False
                
        except requests.exceptions.ConnectionError as e:
            print(f"\n🔌 Connection error on attempt {attempt + 1}: {str(e)[:200]}...")
            if attempt < max_retries - 1:
                wait_time = 30 * (attempt + 1)
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            else:
                print("❌ Max retries exceeded due to connection errors")
                return False
                
        except FileNotFoundError:
            print(f"\n📂 Upgrade file not found: {upgrade_file}")
            return False
            
        except Exception as e:
            print(f"\n💥 Unexpected error on attempt {attempt + 1}: {str(e)[:200]}...")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting 30 seconds before retry...")
                time.sleep(30)
                continue
            else:
                print("❌ Max retries exceeded due to unexpected errors")
                return False
    
    return False


def _upload_with_toolbelt(url, upgrade_file, bytes_size):
    """Upload using requests-toolbelt for optimal performance"""
    try:
        # Track upload progress
        last_percent = [0]  # Use list to make it mutable in closure
        
        def progress_callback(monitor):
            """Callback for upload progress"""
            percent = int((monitor.bytes_read / monitor.len) * 100)
            if percent != last_percent[0] and percent % 5 == 0:  # Update every 5%
                mb_uploaded = monitor.bytes_read / (1024*1024)
                total_mb = monitor.len / (1024*1024)
                print(f"\r   ⬆️  {percent}% - {mb_uploaded:.1f} MB / {total_mb:.1f} MB", end='', flush=True)
                last_percent[0] = percent
        
        # Open file and create multipart encoder
        with open(upgrade_file, 'rb') as f:
            # Create multipart encoder - this will read the file in chunks
            encoder = MultipartEncoder(
                fields={
                    'Filedata': (os.path.basename(upgrade_file), f, 'application/octet-stream')
                }
            )
            
            # Wrap encoder with progress monitor
            monitor = MultipartEncoderMonitor(encoder, progress_callback)
            
            # Upload with streaming to avoid memory issues
            response = session.post(
                url, 
                data=monitor,
                headers={'Content-Type': monitor.content_type},
                verify=False, 
                timeout=1800  # 30 minutes
            )
            
        print()  # New line after progress
            
        if response.status_code != 200:
            print(f"❌ Upload failed with status code: {response.status_code}")
            if hasattr(response, 'text') and response.text:
                print(f"📝 Response: {response.text[:500]}...")
            return False
        
        return True
        
    except Exception as e:
        print(f"💥 Toolbelt upload failed: {str(e)[:200]}...")
        return False


def _upload_with_fallback(url, upgrade_file, bytes_size):
    """Fallback chunked upload method without requests-toolbelt"""
    try:
        class SimpleFileReader:
            def __init__(self, file_path, file_size):
                self.file = open(file_path, 'rb')
                self.file_size = file_size
                self.bytes_read = 0
                self.last_percent = -1
                
            def read(self, size=65536):  # 64KB chunks
                chunk = self.file.read(size)
                self.bytes_read += len(chunk)
                
                percent = int((self.bytes_read / self.file_size) * 100)
                if percent != self.last_percent and percent % 5 == 0:  # Update every 5%
                    mb_uploaded = self.bytes_read / (1024*1024)
                    total_mb = self.file_size / (1024*1024)
                    print(f"\r   ⬆️  {percent}% - {mb_uploaded:.1f} MB / {total_mb:.1f} MB", end='', flush=True)
                    self.last_percent = percent
                    
                return chunk
            
            def __len__(self):
                return self.file_size
                
            def close(self):
                self.file.close()
        
        file_reader = SimpleFileReader(upgrade_file, bytes_size)
        try:
            files = {'Filedata': (os.path.basename(upgrade_file), file_reader, 'application/octet-stream')}
            response = session.post(url, files=files, verify=False, timeout=1800)
        finally:
            file_reader.close()
            print()  # New line after progress
            
        if response.status_code != 200:
            print(f"❌ Upload failed with status code: {response.status_code}")
            if hasattr(response, 'text') and response.text:
                print(f"📝 Response: {response.text[:500]}...")
            return False
        
        return True
        
    except Exception as e:
        print(f"💥 Fallback upload failed: {str(e)[:200]}...")
        return False


def update_status(base_url):
    """Enhanced update status check with multiple fallback methods"""
    try:
        # Primary method: Check settings base params
        url = f"{base_url}/mgmt/system/config/item/settingsbaseparams"
        response = session.get(url, verify=False, timeout=30)
        
        if response.status_code == 200 and response.text.strip():
            return response.json()
        elif response.status_code == 401:
            # Session expired - return None to trigger re-login
            print("\n🔑 Session expired - will attempt re-login", flush=True)
            return None
        
        # Fallback method 1: Check system status
        fallback_url = f"{base_url}/mgmt/system/status"
        fallback_response = session.get(fallback_url, verify=False, timeout=20)
        
        if fallback_response.status_code == 200 and fallback_response.text.strip():
            fallback_data = fallback_response.json()
            # If we can get system status, server is responding but update might be in progress
            return {"lastUpgradeStatus": "In Progress", "software_version": fallback_data.get("version", "Unknown")}
        elif fallback_response.status_code == 401:
            # Session expired - return None to trigger re-login
            print("\n🔑 Session expired - will attempt re-login", flush=True)
            return None
        
        # If both fail, server might be rebooting
        return None
        
    except requests.exceptions.Timeout:
        print("\n⏰ Status check timed out - server may be rebooting", flush=True)
        return None
    except requests.exceptions.ConnectionError:
        print("\n🔄 Connection lost - server rebooting...", flush=True)
        return None
    except requests.exceptions.JSONDecodeError as e:
        print(f"\n📊 JSON decode error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\n🔄 Request error: {e} - server may be rebooting...", flush=True)
        return None


def download_df_config(base_url):
    
    print('Exporting DefenseFlow Configuration from Vision')
    url = f"{base_url}/mgmt/device/df/config/getfromdevice?saveToDb=false&type=config"
    response = session.get(url, stream=True, verify=False)
    
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
        r = session.post(url, files=files, verify=False)
        
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
    """Enhanced version update monitoring with timeout and better progress detection"""
    print(f"\n📊 Monitoring Update Progress")
    print(f"{'='*50}")
    
    ver_update = True
    version = update_status(base_url)
    current_version = version.get('software_version') if version else None
    start_time = time.time()
    check_count = 0
    consecutive_failures = 0
    max_consecutive_failures = 20  # Allow up to 20 consecutive failures (10 minutes)
    
    # Progress indicators
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    print(f"🎯 Starting version: {current_version}")
    print(f"⏱️  Maximum wait time: ~45 minutes")
    
    while ver_update:
        check_count += 1
        elapsed_time = int(time.time() - start_time)
        
        # Safety timeout after 45 minutes
        if elapsed_time > 2700:  # 45 minutes
            print(f"\n⏰ Update monitoring timeout reached (45 minutes)")
            print(f"💡 The update may still be in progress. Check the web interface at: {base_url}")
            response = input("Continue waiting? (y/n): ").lower().strip()
            if response in ['n', 'no']:
                print("🛑 Monitoring stopped by user. Update may still be in progress.")
                return
            else:
                start_time = time.time()  # Reset timer
                consecutive_failures = 0
        
        update_result = update_status(base_url)
        
        # Handle case where update_status returns None due to error
        if update_result is None:
            consecutive_failures += 1
            print(f"\r{spinner[check_count % len(spinner)]} Server not responding... ({consecutive_failures}/15 attempts) ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            
            # Try to re-login after several failures (server might have rebooted)
            if consecutive_failures >= 5 and consecutive_failures % 3 == 0:
                print(f"\n🔑 Attempting to re-login after server reboot...")
                if login(base_url, username, password):
                    print("✅ Re-login successful after reboot")
                    consecutive_failures = 0  # Reset counter after successful login
                else:
                    print("❌ Re-login failed - server may still be rebooting")
            
            if consecutive_failures >= max_consecutive_failures:
                print(f"\n⚠️  Server has been unresponsive for too long ({consecutive_failures} attempts)")
                print(f"💡 This usually means the update is progressing and the server is rebooting")
                print(f"🌐 You can check progress at: {base_url}")
                response = input("Continue waiting? (y/n): ").lower().strip()
                if response in ['n', 'no']:
                    print("🛑 Monitoring stopped by user")
                    return
                else:
                    consecutive_failures = 0  # Reset counter
            
            time.sleep(30)
            continue
        else:
            consecutive_failures = 0  # Reset failure counter on successful response
            
        # Check for completion
        upgrade_status = update_result.get('lastUpgradeStatus', 'In Progress')
        new_version = update_result.get('software_version', current_version)
        
        if (upgrade_status == 'OK' and new_version != current_version):
            ver_update = False
            print(f"\n✅ Version update completed successfully!")
            print(f"🎯 Previous version: {current_version}")
            print(f"🎯 New version: {new_version}")
            print(f"⏱️  Total time: {elapsed_time//60:02d}:{elapsed_time%60:02d}")
        elif upgrade_status == 'Failed':
            print(f"\n❌ Update failed according to server status")
            print(f"💡 Check the web interface for more details: {base_url}")
            return
        else:
            print(f"\r{spinner[check_count % len(spinner)]} Update in progress... Status: {upgrade_status} | Version: {new_version} ({elapsed_time//60:02d}:{elapsed_time%60:02d})", end='', flush=True)
            time.sleep(20)  # Slightly longer wait for more stable monitoring

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
