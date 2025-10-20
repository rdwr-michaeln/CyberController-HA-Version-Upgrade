# CyberController HA Version Upgrade

An automated tool for managing High Availability (HA) version upgrades on Radware Cyber Controller systems. This tool streamlines the complex process of upgrading both primary and secondary controllers while maintaining configuration integrity and system availability.

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

## 📖 Usage

### Quick Start
Run the main script:
```bash
python main.py
```

### Pre-Upload Validation (Recommended for Large Files)
For large upgrade files (>5GB), run the validation utility first:
```bash
python validate_upload.py
```

### Resume from Checkpoint
If the script was interrupted, it will automatically detect the checkpoint and offer to resume:
```bash
python main.py
# Choose 'n' when asked "Do you want to start fresh?"
```

The script will prompt you for:
- Primary Cyber-Controller IP address
- Primary controller credentials (username/password)
- Secondary Cyber-Controller IP address  
- Secondary controller credentials (username/password)
- Path to the upgrade file (.tar.gz)

## 🔄 Upgrade Process

The automation follows a 7-phase process:

1. **Phase 1: Disable HA** - Safely disables HA on the primary controller
2. **Phase 2: Update Secondary** - Performs version upgrade on secondary controller
3. **Phase 3: Config Migration to Secondary** - Exports config from primary and imports to secondary
4. **Phase 4: Update Primary** - Performs version upgrade on primary controller
5. **Phase 5: Config Migration to Primary** - Exports config from secondary and imports to primary
6. **Phase 6: Configure Router ID** - Updates network elements and protected objects on secondary
7. **Phase 7: Re-establish HA** - Restores HA configuration and waits for healthy status

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

## ⚠️ Important Notes

- **Backup**: Always backup your configuration before running upgrades
- **Network Access**: Ensure stable network connectivity throughout the process
- **Large Files**: For files >5GB, expect 30+ minutes upload time per controller
- **Memory Requirements**: Ensure sufficient RAM for large file processing
- **Credentials**: Use administrator-level accounts with full API access
- **File Path**: Provide the full path to your upgrade file
- **Licensing**: CyberController Plus license required for configuration migration
- **Monitoring**: Monitor the process and be prepared to intervene if needed
- **Checkpoints**: Progress is automatically saved and can be resumed

## 🐛 Troubleshooting

### Common Issues
- **Login Failures**: Verify credentials and network connectivity
- **Upload Timeouts**: Check file size and network bandwidth
- **SSL/Connection Errors**: See `large_file_troubleshooting.md` for detailed solutions
- **HA Status Issues**: Ensure both controllers are responsive
- **Configuration Errors**: Verify API permissions and controller versions
- **Memory Issues**: Free up system memory for large files
- **License Issues**: Ensure valid CyberController Plus license

### Recovery Options
- **Checkpoint Resume**: Restart script and choose to resume from last checkpoint
- **Manual Recovery**: Follow procedures in `manual_recovery_guide.md`
- **Pre-validation**: Run `validate_upload.py` before starting upgrades

### Large File Issues
For files >5GB experiencing upload problems:
1. Check `large_file_troubleshooting.md` for detailed solutions
2. Run `validate_upload.py` to check prerequisites
3. Consider manual upload via web interface
4. Ensure stable network and sufficient system resources

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

## ⚡ Version History

- **v2.0.0** - Enhanced Large File Support
  - Chunked upload for multi-GB files
  - Memory management and garbage collection
  - SSL error handling improvements
  - Checkpoint system for resume capability
  - License validation
  - Pre-upload validation utility
  - Comprehensive troubleshooting guides
- **v1.0.0** - Initial release with full HA automation support
  - Organized modular architecture
  - Comprehensive error handling
  - Phase-based upgrade process

---

**Warning**: This tool performs critical system operations. Always test in a development environment before using in production.
