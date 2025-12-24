# CyberController HA Version Upgrade

An automated tool for managing High Availability (HA) version upgrades on Radware Cyber Controller systems. This tool streamlines the complex process of upgrading both primary and secondary controllers while maintaining configuration integrity and system availability.

## 🔧 Features

- **Automated HA Management**: Automatically disables and re-establishes HA during upgrade process
- **Dual Controller Support**: Handles both primary and secondary controller upgrades
- **Configuration Migration**: Exports and imports DefenseFlow configurations between controllers
- **Router ID Management**: Automatically configures network elements with proper router IDs
- **Protected Objects Handling**: Manages protected object states during upgrade
- **Progress Monitoring**: Real-time status updates and progress tracking
- **Error Handling**: Comprehensive error detection and recovery mechanisms

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

Run the main script:
```bash
python main.py
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
├── main.py                 # Main automation script
├── ha_functions.py         # Core functions and API interactions
├── .gitignore             # Git ignore rules
├── README.md              # This file
└── requirements.txt       # Python dependencies
```

## 🔧 Functions Overview

### Core Functions (`ha_functions.py`)
- `login()` - Authenticate with controllers
- `break_ha()` - Disable HA configuration
- `establish_ha()` - Enable HA configuration
- `version_update()` - Upload and apply version updates
- `download_df_config()` - Export DefenseFlow configuration
- `upload_df_config()` - Import DefenseFlow configuration
- `get_router_id()` - Retrieve BGP router ID
- `get_net_element_names()` - Get network element names
- `get_po_names()` - Get protected object names

### Helper Functions
- `wait_for_ha_disable()` - Monitor HA disable process
- `wait_for_version_update()` - Monitor update completion
- `wait_for_ha_healthy()` - Monitor HA health status
- `disable_protected_objects()` - Disable all protected objects
- `update_network_elements_router_id()` - Update router IDs

## ⚠️ Important Notes

- **Backup**: Always backup your configuration before running upgrades
- **Network Access**: Ensure stable network connectivity throughout the process
- **Credentials**: Use administrator-level accounts with full API access
- **File Path**: Provide the full path to your upgrade file
- **Monitoring**: Monitor the process and be prepared to intervene if needed

## 🐛 Troubleshooting

- **Login Failures**: Verify credentials and network connectivity
- **Upload Timeouts**: Check file size and network bandwidth
- **HA Status Issues**: Ensure both controllers are responsive
- **Configuration Errors**: Verify API permissions and controller versions

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

- **v1.0.0** - Initial release with full HA automation support
- Organized modular architecture
- Comprehensive error handling
- Phase-based upgrade process

---

**Warning**: This tool performs critical system operations. Always test in a development environment before using in production.
