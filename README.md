# CyberController HA Version Upgrade Automation

## 📖 Overview

This is a comprehensive automation tool designed to manage **High Availability (HA) version upgrades** on Radware CyberController systems. The tool orchestrates the complex process of upgrading both primary and secondary controllers while maintaining configuration integrity, minimizing downtime, and ensuring system availability throughout the upgrade process.

### Why This Tool?

Manual HA upgrades are complex, time-consuming, and error-prone. This automation:
- **Eliminates human errors** in the multi-step upgrade process
- **Reduces downtime** through optimized sequencing
- **Handles large files** (multi-GB upgrades) efficiently
- **Provides recovery options** if something goes wrong
- **Maintains configuration consistency** between controllers

## 🔧 Features

- **Automated HA Management**: Automatically disables and re-establishes HA during upgrade process
- **Dual Controller Support**: Handles both primary and secondary controller upgrades
- **Large File Support**: Optimized for handling multi-GB upgrade files with chunked uploads
- **Configuration Migration**: Exports and imports DefenseFlow configurations between controllers
- **License Validation**: Checks CyberController Plus license before configuration migration
- **Router ID Management**: Automatically configures network elements with proper router IDs
- **Protected Objects Handling**: Manages protected object states during upgrade
- **Progress Monitoring**: Real-time status updates and progress tracking with keep-alive
- **Checkpoint System**: Saves progress and allows resuming from interruptions
- **Error Handling**: Comprehensive error detection and recovery mechanisms
- **Memory Management**: Efficient handling of large files with garbage collection

## 📋 Prerequisites

- Python 3.6 or higher
- Network access to both primary and secondary Cyber Controllers
- Administrator credentials for both controllers
- Upgrade file (.tar.gz format)
- Required Python packages (see requirements.txt)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/rdwr-michaeln/CyberController-HA-Version-Upgrade.git
cd CyberController-HA-Version-Upgrade
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## 📖 Step-by-Step Usage Guide

### Step 1: Pre-Upgrade Preparation

#### System Requirements Check
```bash
# Check available memory (need ~2GB+ for large files)
free -h

# Check available disk space (need ~20% of upgrade file size)
df -h .

# Verify Python version
python3 --version
```

#### Network Connectivity Test
```bash
# Test connectivity to both controllers
ping <primary-controller-ip>
ping <secondary-controller-ip>

# Test HTTPS access
curl -k https://<primary-controller-ip>/mgmt/system/status
curl -k https://<secondary-controller-ip>/mgmt/system/status
```

### Step 2: Pre-Upload Validation (Recommended)

**For large upgrade files (>5GB), always run validation first:**
```bash
python validate_upload.py
```

This utility will check:
- ✅ File existence and readability
- ✅ Available system memory and disk space
- ✅ Network connectivity to controllers
- ✅ Authentication credentials
- ✅ Estimated upload time

### Step 3: Run the Main Upgrade

#### First Time / Fresh Start
```bash
python main.py
```

#### Resume from Interruption
If the script was interrupted, it will automatically detect the checkpoint:
```bash
python main.py
# When prompted: "Do you want to start fresh? (y/n):"
# Choose 'n' to resume from last checkpoint
```

### Step 4: Input Required Information

The script will prompt you for the following information in order:

#### Primary Controller Configuration
```
Primary CyberController address: 192.168.1.100
Primary username: admin
Primary password: ********
```

#### Secondary Controller Configuration
```
Secondary CyberController address: 192.168.1.101
Secondary username: admin
Secondary password: ********
```

#### Upgrade File Details
```
Upgrade file path (.tar.gz): /path/to/upgrade-file.tar.gz
```

**File Size Warning**: For files >5GB, you'll see a warning about expected upload time and can choose to continue or cancel.

### Step 5: Monitor Progress

The script provides real-time feedback:

```
🚀 Radware CyberController HA Version Upgrade Automation
========================================================

📋 Found previous session from 2025-10-20T10:30:00Z
Last completed: Phase 2 - completed
Do you want to start fresh? (y/n): n
🔄 Resuming from Phase 3

📋 Phase 3: Migrating Configuration to Secondary
------------------------------------------------
🔍 Checking License Validity
✅ Valid CyberController Plus License found
✅ Login successful
Exporting DefenseFlow Configuration from Vision
✅ Successfully Exported File DefenseFlowConfiguration_20251020_103500.zip
✅ Login successful
Successfully Migrated DefenseFlow Configuration to Cyber-Controller Plus
💾 Progress saved: Phase 3 - completed
```

### Step 6: Handle Interruptions (If Needed)

#### If Process is Interrupted
- **Ctrl+C**: Gracefully saves progress to checkpoint
- **System reboot**: Progress is saved automatically
- **Network issue**: Resume from last completed phase

#### To Resume
```bash
python main.py
# Choose 'n' when asked about starting fresh
# Script continues from last successful phase
```

### Step 7: Verify Completion

When successful, you'll see:
```
🎉 All phases completed successfully!
✅ HA upgrade automation finished
📁 Checkpoint archived as: checkpoint_completed_20251020_143000.json
```

#### Post-Upgrade Verification
1. **Check HA Status**: Verify both controllers show "healthy"
2. **Version Verification**: Confirm both controllers have the new version
3. **Configuration Check**: Ensure all configurations are properly migrated
4. **Network Elements**: Verify router IDs are correctly configured

## 🔄 Detailed Upgrade Process

The automation follows a carefully orchestrated **7-phase process** to ensure safe and reliable upgrades:

### Phase 1: Disable HA Configuration
- **Purpose**: Safely break the HA relationship to allow independent upgrades
- **Actions**: 
  - Connects to primary controller
  - Disables HA configuration
  - Waits for HA status to show "disabled"
- **Duration**: ~2-5 minutes
- **Checkpoint**: ✅ Saved after completion

### Phase 2: Update Secondary Controller
- **Purpose**: Upgrade the secondary controller first (safer approach)
- **Actions**:
  - Validates upload prerequisites (file, connectivity, resources)
  - Authenticates to secondary controller
  - Uploads upgrade file (.tar.gz)
  - Initiates version update process
  - Monitors update progress until completion
- **Duration**: 15-45 minutes (depending on file size)
- **Checkpoint**: ✅ Saved after completion

### Phase 3: Configuration Migration to Secondary
- **Purpose**: Export current config from primary and import to updated secondary
- **Actions**:
  - Checks for valid CyberController Plus license
  - Exports DefenseFlow configuration from primary
  - Downloads configuration file locally
  - Uploads configuration to secondary controller
  - Verifies successful import
- **Duration**: ~5-10 minutes
- **Note**: Skipped if no valid CyberController Plus license
- **Checkpoint**: ✅ Saved after completion

### Phase 4: Update Primary Controller
- **Purpose**: Upgrade the primary controller with the same version
- **Actions**:
  - Validates upload prerequisites
  - Authenticates to primary controller
  - Uploads upgrade file (.tar.gz)
  - Initiates version update process
  - Monitors update progress until completion
- **Duration**: 15-45 minutes (depending on file size)
- **Checkpoint**: ✅ Saved after completion

### Phase 5: Configuration Migration to Primary
- **Purpose**: Sync configuration from updated secondary back to primary
- **Actions**:
  - Exports latest DefenseFlow configuration from secondary
  - Downloads configuration file locally
  - Uploads configuration to primary controller
  - Verifies successful import
- **Duration**: ~5-10 minutes
- **Note**: Skipped if no valid CyberController Plus license
- **Checkpoint**: ✅ Saved after completion

### Phase 6: Configure Secondary Router ID
- **Purpose**: Update network elements and protected objects on secondary
- **Actions**:
  - Retrieves BGP router ID from secondary controller
  - Disables all protected objects temporarily
  - Updates network element router IDs
  - Configures proper routing for HA operation
- **Duration**: ~3-8 minutes
- **Checkpoint**: ✅ Saved after completion

### Phase 7: Re-establish HA
- **Purpose**: Restore HA relationship and verify healthy operation
- **Actions**:
  - Connects to primary controller
  - Configures HA with secondary controller details
  - Initiates HA establishment
  - Monitors HA health status
  - Waits for both controllers to show "healthy"
- **Duration**: ~5-15 minutes
- **Checkpoint**: ✅ Saved after completion

### 🎯 Total Estimated Time
- **Small files (<1GB)**: 45-90 minutes
- **Large files (5-10GB)**: 90-180 minutes
- **Factors affecting time**: File size, network speed, controller performance

## 📁 Project Structure

```
├── main.py                          # Main automation script with checkpoint support
├── ha_functions.py                  # Core functions and API interactions
├── validate_upload.py               # Pre-upload validation utility
├── large_file_troubleshooting.md    # Guide for large file upload issues
├── manual_recovery_guide.md         # Manual recovery procedures
├── checkpoint.json                  # Progress checkpoint (auto-generated)
├── .gitignore                       # Git ignore rules
├── README.md                        # This file
└── requirements.txt                 # Python dependencies
```

## 🔧 Functions Overview

### Core Functions (`ha_functions.py`)
- `login()` - Authenticate with controllers
- `break_ha()` - Disable HA configuration
- `establish_ha()` - Enable HA configuration
- `version_update()` - Upload and apply version updates with chunked upload support
- `download_df_config()` - Export DefenseFlow configuration
- `upload_df_config()` - Import DefenseFlow configuration
- `get_router_id()` - Retrieve BGP router ID
- `get_net_element_names()` - Get network element names
- `get_po_names()` - Get protected object names
- `get_license()` - Check CyberController Plus license validity
- `validate_upload_prerequisites()` - Validate system requirements before upload

### Helper Functions
- `wait_for_ha_disable()` - Monitor HA disable process
- `wait_for_version_update()` - Monitor update completion
- `wait_for_ha_healthy()` - Monitor HA health status
- `disable_protected_objects()` - Disable all protected objects
- `update_network_elements_router_id()` - Update router IDs

### Checkpoint Management
- `save_progress()` - Save current phase progress
- `load_progress()` - Load previous session progress
- `archive_checkpoint()` - Archive completed sessions

## ⚠️ Critical Requirements & Warnings

### 🔒 Security & Access Requirements
- **Administrator Access**: Use accounts with full administrative privileges
- **API Access**: Ensure accounts have API access enabled
- **Network Access**: Both controllers must be accessible via HTTPS
- **Firewall**: Ensure ports 443 (HTTPS) and any custom management ports are open

### 💾 Backup & Safety
- **⚠️ CRITICAL**: Always backup your configuration before starting
- **Configuration Export**: Manual backup of DefenseFlow configurations
- **System Snapshot**: Consider VM snapshots if running virtualized
- **Rollback Plan**: Have a rollback procedure ready

### 🌐 Network & Performance
- **Stable Connection**: Use wired network connections (avoid WiFi for large files)
- **Bandwidth**: Minimum 10Mbps recommended for large files
- **Latency**: Low latency connection preferred (< 100ms)
- **Uninterrupted Access**: Ensure no network maintenance during upgrade window

### 💻 System Resources
- **Memory**: Minimum 4GB available RAM (8GB+ recommended for >5GB files)
- **Disk Space**: At least 3x the upgrade file size in free space
- **CPU**: Monitor system load during upload (keep < 80%)

### 📦 File Requirements
- **Format**: Upgrade file must be in .tar.gz format
- **Integrity**: Verify file checksum before starting
- **Accessibility**: Ensure full read access to upgrade file
- **Path**: Use absolute paths to avoid issues

### 🏥 Licensing
- **CyberController Plus**: Required for configuration migration
- **License Validity**: Must be valid and not expired
- **Migration Impact**: Without valid license, configurations won't be migrated
- **Manual Backup**: If no license, manually backup configurations

### ⏱️ Time Planning
- **Maintenance Window**: Plan for 2-4 hour maintenance window
- **Large Files**: Files >5GB can take 30+ minutes per controller to upload
- **Business Hours**: Avoid during peak business hours
- **Rollback Time**: Account for potential rollback time in planning

### 🔍 Monitoring Requirements
- **Console Access**: Monitor the automation console throughout
- **Controller Access**: Maintain browser access to both controllers
- **Network Monitoring**: Watch for connection issues
- **Intervention Ready**: Be prepared to manually intervene if needed

## � Troubleshooting & Problem Resolution

### 🔧 Quick Diagnostics

#### Check System Status
```bash
# System resources
free -h && df -h . && ps aux | grep python

# Network connectivity
ping -c 3 <controller-ip>
curl -k -w "%{http_code}\n" https://<controller-ip>/mgmt/system/status

# Process status
ps aux | grep main.py
```

### 🚫 Common Issues & Solutions

#### Authentication Problems
| **Problem** | **Symptoms** | **Solution** |
|-------------|--------------|--------------|
| Login Failures | "❌ Login failed with status code: 401" | Verify credentials, check account permissions |
| Session Expired | "🔑 Session expired, re-authenticating..." | Normal behavior - script handles automatically |
| API Access Denied | "❌ Login failed" with 403 | Ensure account has API access enabled |

#### Upload Issues
| **Problem** | **Symptoms** | **Solution** |
|-------------|--------------|--------------|
| Upload Timeouts | "⏰ Upload timed out" | Check network stability, use wired connection |
| SSL Errors | "SSLEOFError" or "SSL connection error" | See `large_file_troubleshooting.md` |
| Memory Issues | Process "Killed" or out of memory | Free system memory, close other applications |
| File Not Found | "📂 Upgrade file not found" | Verify file path and permissions |

#### HA Status Issues
| **Problem** | **Symptoms** | **Solution** |
|-------------|--------------|--------------|
| HA Won't Disable | Stuck in "Waiting for HA to be disabled" | Check controller responsiveness, manual verification |
| HA Won't Establish | Stuck in "Re-establishing HA" | Verify network connectivity between controllers |
| Controllers Not Healthy | HA shows unhealthy status | Check controller logs, verify configurations |

### 🔄 Recovery Procedures

#### Automatic Recovery (Recommended)
```bash
# Resume from checkpoint
python main.py
# Choose 'n' when asked "Do you want to start fresh?"
```

#### Manual Recovery Steps
1. **Check Current State**:
   ```bash
   # View checkpoint
   cat checkpoint.json
   
   # Check controller status via web interface
   # https://<controller-ip>
   ```

2. **Phase-Specific Recovery**:
   - **Phase 1-2**: If HA disabled, check secondary controller status
   - **Phase 3-5**: Verify configuration migration status
   - **Phase 6-7**: Check HA establishment progress

3. **Complete Manual Recovery**:
   See detailed procedures in `manual_recovery_guide.md`

### 📊 Large File Specific Issues

#### For Files >5GB experiencing problems:

1. **Pre-flight Check**:
   ```bash
   python validate_upload.py
   ```

2. **System Optimization**:
   ```bash
   # Free memory
   sudo sync && sudo sysctl vm.drop_caches=3
   
   # Check available space
   df -h .
   
   # Monitor during upload
   watch -n 30 'free -h && netstat -i'
   ```

3. **Alternative Upload Methods**:
   - Manual upload via web interface
   - Upload from machine with better network connection
   - Split maintenance window if needed

### 🆘 Emergency Procedures

#### If Automation Fails Completely
1. **Immediate Actions**:
   - Don't panic - controllers are likely still functional
   - Check both controllers via web interface
   - Document current state

2. **Assessment**:
   - Which phase failed?
   - Are both controllers accessible?
   - Is HA currently enabled or disabled?

3. **Recovery Options**:
   - **Option A**: Resume automation from checkpoint
   - **Option B**: Complete remaining steps manually
   - **Option C**: Rollback to previous state (if backups available)

#### Emergency Contacts
- **Radware Support**: Contact for controller-specific issues
- **Network Team**: For connectivity problems
- **System Administrator**: For system resource issues

### 📞 Getting Help

#### Information to Collect Before Seeking Help
1. **Console Output**: Copy all console output from the script
2. **Checkpoint File**: Content of `checkpoint.json`
3. **System Info**: `free -h`, `df -h`, `python --version`
4. **Controller Status**: Screenshots from web interfaces
5. **Error Messages**: Exact error messages and stack traces

#### Support Resources
1. **GitHub Issues**: Create issue with collected information
2. **Documentation**: Check `large_file_troubleshooting.md` and `manual_recovery_guide.md`
3. **Logs**: Review console output for specific error patterns

## 📝 Logging

The script provides detailed console output for each phase. For additional logging, check:
- Console output for real-time status
- Error messages for troubleshooting
- Progress indicators for each phase

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in this repository
- Check the troubleshooting section above
- Review the console output for detailed error messages

## 📋 Example Workflow

### Typical Successful Run Output
```bash
$ python main.py

🚀 Radware CyberController HA Version Upgrade Automation
========================================================

🚀 HA Automation Setup
======================
Primary CyberController address: 192.168.1.100
Primary username: admin
Primary password: ********
Secondary CyberController address: 192.168.1.101
Secondary username: admin
Secondary password: ********
Upgrade file path (.tar.gz): /home/admin/upgrade-v10.2.tar.gz

Starting HA automation process...
Primary: 192.168.1.100
Secondary: 192.168.1.101
Upgrade file: /home/admin/upgrade-v10.2.tar.gz (1024.50 MB)

🔍 Checking License Validity
Checking license on primary controller...
✅ Login successful
✅ Valid CyberController Plus License found
Configuration migration will be performed during upgrade

📋 Phase 1: Disabling HA
-------------------------
💾 Progress saved: Phase 1 - starting
✅ Login successful
HA going to Disable state
🔄 Waiting for HA to be disabled...
✅ HA is now disabled! (took 02:15)
💾 Progress saved: Phase 1 - completed

📋 Phase 2: Updating Secondary Controller
-----------------------------------------
💾 Progress saved: Phase 2 - starting
🔍 Validating Upload Prerequisites
✅ File validation passed
✅ Server connectivity verified
✅ Login successful

🔄 Starting Version Update
============================================================
📁 File: upgrade-v10.2.tar.gz
📊 Size: 1024.50 MB (1,073,741,824 bytes)
🎯 Target: 192.168.1.101
============================================================
⬆️  Uploading file... This may take several minutes...
🔄 Keep-alive started (5 minute intervals)
[2025-10-20 14:15:30] Keep-alive sent - Status: 200
🛑 Keep-alive stopped
✅ File uploaded successfully!
⏳ Processing uploaded file...
🚀 Starting system update...
📊 Monitoring Update Progress
⏱️  Total time: 28:45
💾 Progress saved: Phase 2 - completed

... [Phases 3-7 continue similarly] ...

🎉 All phases completed successfully!
✅ HA upgrade automation finished
📁 Checkpoint archived as: checkpoint_completed_20251020_153000.json
```

## ⚡ Version History & Changelog

### **v2.0.0** - Enhanced Large File Support (Current)
**Release Date**: October 2025

#### 🆕 New Features
- **Enhanced SSL Handling**: Custom HTTP adapters for better connection stability
- **Improved Keep-Alive**: 5-minute intervals to maintain session during long uploads
- **Checkpoint System**: Automatic progress saving with resume capability
- **License Validation**: Checks CyberController Plus license before configuration migration
- **Pre-Upload Validation**: `validate_upload.py` utility for system prerequisite checks
- **Comprehensive Documentation**: Detailed troubleshooting guides and recovery procedures

#### 🔧 Improvements
- **Better Error Handling**: Enhanced retry logic with exponential backoff
- **Connection Management**: Improved SSL error recovery and connection persistence
- **Progress Monitoring**: Real-time status updates and progress indicators
- **Memory Optimization**: Better handling of large files and system resources
- **Timeout Management**: Dynamic timeout calculation based on file size

#### 🐛 Bug Fixes
- **SSL EOF Errors**: Fixed SSL connection termination issues during large uploads
- **Process Termination**: Resolved "Killed" process issues with large files
- **Session Management**: Improved session persistence and re-authentication
- **Connection Drops**: Better handling of network interruptions

#### 📚 Documentation
- **README**: Comprehensive step-by-step usage guide
- **Troubleshooting**: Detailed problem resolution procedures
- **Recovery Guide**: Manual recovery procedures for failed automation

### **v1.0.0** - Initial Release
**Release Date**: September 2025

#### 🆕 Initial Features
- **7-Phase Automation**: Complete HA upgrade workflow
- **Dual Controller Support**: Handles both primary and secondary controllers
- **Configuration Migration**: DefenseFlow configuration export/import
- **Router ID Management**: Automatic network element configuration
- **Protected Objects**: Automated protected object management
- **HA Management**: Automatic HA disable/enable with health monitoring

#### 🏗️ Architecture
- **Modular Design**: Separated core functions and main workflow
- **API Integration**: RESTful API communication with controllers
- **Error Handling**: Basic error detection and reporting
- **Progress Tracking**: Phase-based progress indication

## 🎯 Best Practices & Recommendations

### 🕐 Planning & Scheduling
- **Maintenance Window**: Schedule 3-4 hour maintenance window
- **Off-Peak Hours**: Perform upgrades during low-traffic periods
- **Advance Notice**: Notify users of potential service interruption
- **Rollback Plan**: Have rollback procedure documented and tested

### 🔄 Pre-Upgrade Testing
- **Development Environment**: Test the entire process in dev/staging first
- **File Validation**: Verify upgrade file integrity and compatibility
- **Connectivity Test**: Ensure stable network connectivity to both controllers
- **Resource Check**: Verify sufficient system resources (memory, disk, CPU)

### 📊 During Upgrade
- **Active Monitoring**: Monitor both the automation script and controller web interfaces
- **Network Stability**: Avoid any network changes during the upgrade process
- **Resource Monitoring**: Watch system resources (memory, CPU, disk I/O)
- **Documentation**: Log any issues or observations for future reference

### ✅ Post-Upgrade Verification
- **Version Confirmation**: Verify both controllers show the correct new version
- **HA Health Check**: Confirm HA status shows "healthy" on both nodes
- **Configuration Verification**: Spot-check critical configurations
- **Functionality Test**: Test key functionality to ensure everything works
- **Performance Check**: Monitor system performance post-upgrade

### 🔒 Security Considerations
- **Credential Management**: Use dedicated service accounts with minimal required permissions
- **Network Security**: Ensure upgrade is performed from trusted network segment
- **Audit Logging**: Enable and review audit logs for the upgrade process
- **Access Control**: Limit who has access to the upgrade files and scripts

---

## ⚠️ **IMPORTANT WARNINGS**

> **🚨 CRITICAL**: This tool performs system-level operations on production infrastructure. Always:
> - Test thoroughly in a development environment first
> - Have a complete backup and rollback plan
> - Perform upgrades during scheduled maintenance windows
> - Monitor the process actively throughout
> - Be prepared to intervene manually if needed

> **📋 DISCLAIMER**: While this automation significantly reduces the complexity and risk of HA upgrades, the user is ultimately responsible for:
> - Proper testing and validation
> - Backup and recovery procedures  
> - System monitoring and intervention
> - Following organizational change management processes