# THIS IS NOT YET WORKING AND JUST A WIP
If you want a working version, check back here from time to time
If you want to contribute, message me

# JellyDemon - Intelligent Jellyfin Bandwidth Management

A Python daemon that automatically manages Jellyfin user bandwidth limits based on real-time network demand and external streaming activity.

## Current Deployment

This instance is deployed on:
- **Server**: Debian LXC container on Proxmox (192.168.1.208)
- **Project Root**: `/opt/jellydemon`
- **Jellyfin Server**: 192.168.1.243
- **OpenWRT Router**: 192.168.1.1 (root user)
- **Development**: Remote-SSH via VS Code/Cursor with direct terminal access
- **API Documentation**: Full Jellyfin OpenAPI spec available at `jellyfin-openapi-stable.json`

## Project Scope

JellyDemon monitors your network and Jellyfin server to dynamically allocate bandwidth to external users based on:

1. **Network Demand**: Monitors OpenWRT router for current upload bandwidth usage (excluding Jellyfin traffic)
2. **External Streaming**: Identifies Jellyfin users streaming from outside your LAN
3. **Dynamic Allocation**: Calculates and applies appropriate bandwidth limits per user
4. **Automatic Management**: Runs as a daemon with configurable intervals

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenWRT       │    │   JellyDemon    │    │   Jellyfin      │
│   Router        │◄──►│   Daemon        │◄──►│   Server        │
│                 │    │                 │    │                 │
│ • Bandwidth     │    │ • Monitor       │    │ • Active        │
│   monitoring    │    │ • Calculate     │    │   sessions      │
│ • SQM control   │    │ • Apply limits  │    │ • User limits   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Features

- **Real-time Monitoring**: Continuously monitors network and streaming activity
- **External User Detection**: Identifies users streaming from outside configured IP ranges
- **Dynamic Bandwidth Management**: Automatically adjusts user limits based on available bandwidth
- **Smart Session Management**: Handles Jellyfin's bandwidth change behavior with automatic session restart
- **Configurable Algorithms**: Pluggable bandwidth calculation formulas
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Safe Operation**: Validates changes before applying to prevent service disruption
- **Testing Tools**: Includes bandwidth control testing script for validation

## Requirements

- OpenWRT router with LuCI/SSH access (192.168.1.1)
- Jellyfin server with API access (192.168.1.243)
- Python 3.8+ environment (Debian LXC container at 192.168.1.208)
- Network access to both router and Jellyfin server
- Environment variables configured in `.env` file



## Installation

### Quick Setup

```bash
# 1. Navigate to project directory (already deployed)
cd /opt/jellydemon

# 2. Create environment file with credentials
cp .env.example .env
nano .env

# Add these variables to .env:
# JELLY_API=your_jellyfin_api_key_here
# ROOTER_PASS=your_router_password_here

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy example configuration
cp config.example.yml config.yml
nano config.yml

# 5. Test connectivity
python jellydemon.py --test

# 6. Run in dry-run mode first
python jellydemon.py --dry-run
```

### Manual Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create configuration:**
   ```bash
   cp config.example.yml config.yml
   nano config.yml
   ```

3. **Configure environment variables (.env):**
   ```bash
   # Required environment variables
   JELLY_API=your_jellyfin_api_key_here
   ROOTER_PASS=your_router_root_password
   ```

4. **Configure your settings (config.yml):**
   - **Router settings**: OpenWRT router at 192.168.1.1 (username: root)
   - **Jellyfin settings**: Server at 192.168.1.243 (API key from .env)
   - **jellyfin_ip**: IP of your Jellyfin server for traffic exclusion
   - **Network ranges**: Configure your internal IP ranges
   - **Bandwidth settings**: Adjust limits and algorithm preferences

5. **Get Jellyfin API Key:**
   - Go to Jellyfin Admin Dashboard → API Keys
   - Create a new API key for JellyDemon
   - Add the key to your `.env` file as `JELLY_API`

### Testing & Validation

```bash
# Test all components
python test_jellydemon.py

# Test specific components
python test_jellydemon.py --test openwrt
python test_jellydemon.py --test jellyfin

# Test with the main daemon
python jellydemon.py --test
```

## Configuration

### Environment Variables (.env)
```bash
# Jellyfin API key (get from Jellyfin Admin → API Keys)
JELLY_API=your_jellyfin_api_key_here

# OpenWRT router root password
ROOTER_PASS=your_router_root_password
```

### Configuration File (config.yml)
Key configuration options:

- **Router settings**: 192.168.1.1 (username: root, password from .env)
- **Jellyfin settings**: 192.168.1.243 (API key from .env)
- **jellyfin_ip**: IP of your Jellyfin server for traffic exclusion
- **Network ranges**: Define internal/external IP ranges
- **Bandwidth algorithms**: Select calculation method
- **Daemon settings**: Update intervals, logging level

### API Documentation
Full Jellyfin OpenAPI specification is available in `jellyfin-openapi-stable.json` for reference when extending functionality.

### Important Notes on Jellyfin Bandwidth Management

**Bandwidth Changes Require Session Restart**: A critical discovery during development is that Jellyfin bandwidth limit changes do not apply to active streaming sessions. The changes only take effect when:
1. A new session is started, or
2. The existing session is stopped and resumed

For this reason, JellyDemon implements a smart session restart mechanism:
- Detects when bandwidth limits need to be applied to active sessions
- Gracefully stops the current playback at the exact position
- Immediately resumes playback from the same position
- The client experiences a brief buffering period and reconnects with the new bandwidth limit

This behavior has been validated and is handled automatically by the daemon.

## Development Environment

This project is configured for development using:
- **Remote Access**: VS Code/Cursor with Remote-SSH extension
- **Target Server**: Debian LXC container at 192.168.1.208
- **Project Path**: `/opt/jellydemon`
- **Direct Terminal Access**: Available through VS Code/Cursor integrated terminal
- **File Editing**: Direct file editing on the server (no local sync required)

To connect via Remote-SSH:
```bash
# VS Code/Cursor command palette
Remote-SSH: Connect to Host... → 192.168.1.208
```

## Safety Features

- **Dry-run mode**: Test without applying changes
- **Backup/restore**: Save and restore user settings
- **Validation**: Verify API connectivity before operation
- **Graceful shutdown**: Clean exit with settings restoration

## Usage

### Running the Daemon

```bash
# Test connectivity first
python jellydemon.py --test

# Dry run (no changes applied)
python jellydemon.py --dry-run

# Normal operation
python jellydemon.py

# Custom config file
python jellydemon.py --config /path/to/config.yml

# Run as systemd service
sudo systemctl start jellydemon
sudo systemctl enable jellydemon  # Auto-start on boot
```

### Testing and Development

```bash
# Run comprehensive tests
python test_jellydemon.py

# Test specific components
python test_jellydemon.py --test network     # IP range detection
python test_jellydemon.py --test openwrt     # Router connection
python test_jellydemon.py --test jellyfin    # Jellyfin API
python test_jellydemon.py --test bandwidth   # Algorithm testing
python test_jellydemon.py --test integration # Full integration

# Test bandwidth control with real sessions (recommended)
python test_bandwidth_control.py

# Check logs
tail -f jellydemon.log
```

### Bandwidth Control Testing

The `test_bandwidth_control.py` script provides real-world testing of Jellyfin bandwidth management:

1. **Configure test parameters** at the top of the script:
   ```python
   TARGET_IP = "178.165.192.135"  # IP to target
   TARGET_BANDWIDTH = 20.00       # Bandwidth limit in Mbps
   ```

2. **Run the test**:
   ```bash
   python test_bandwidth_control.py
   ```

3. **Test process**:
   - Shows all active streaming sessions with current bandwidth limits
   - Applies new bandwidth limit to specified IP address
   - Optionally forces session restart to apply the limit immediately
   - Verifies the change was applied successfully

This script validates the complete bandwidth control workflow including the session restart mechanism.

## OpenWRT Router Configuration

For your OpenWRT router at 192.168.1.1:

1. **Enable SSH access** (if using SSH method):
   ```bash
   # On router (192.168.1.1)
   uci set dropbear.@dropbear[0].PasswordAuth='on'
   uci commit dropbear
   /etc/init.d/dropbear restart
   ```

2. **Install required packages** (SSH method):
   ```bash
   # On router (192.168.1.1)
   opkg update
   opkg install bc  # For bandwidth calculations
   ```

3. **Configure SQM** (optional, for rate limiting):
   - Install luci-app-sqm package if not already installed
   - Configure basic SQM settings through LuCI interface

## Troubleshooting

### Common Issues

1. **Connection failures:**
   ```bash
   # Test router connectivity
   ping 192.168.1.1
   ssh root@192.168.1.1 "echo test"
   
   # Test Jellyfin API (replace YOUR_API_KEY with value from .env)
   curl -H "Authorization: MediaBrowser Token=YOUR_API_KEY" \
        http://192.168.1.243:8096/System/Info
   ```

2. **Permission errors:**
   ```bash
   # Ensure proper permissions
   chmod +x jellydemon.py
   chmod +x setup.py
   ```

3. **Module import errors:**
   ```bash
   # Check Python path
   python -c "import sys; print(sys.path)"
   
   # Install missing dependencies
   pip install -r requirements.txt
   ```

4. **Bandwidth detection issues:**
   - Check your WAN interface name in OpenWRT
   - Verify SQM configuration if using SSH method
   - Enable debug logging in config.yml

### Debugging

Enable debug logging in `config.yml`:
```yaml
daemon:
  log_level: "DEBUG"
```

Check specific component logs:
```bash
grep "jellydemon.openwrt" jellydemon.log     # Router communication
grep "jellydemon.jellyfin" jellydemon.log    # Jellyfin API calls  
grep "jellydemon.bandwidth" jellydemon.log   # Algorithm calculations
```

## Development Status

This project is in active development. Current implementation provides:
- ✅ Basic daemon framework with signal handling
- ✅ OpenWRT SSH and LuCI API integration
- ✅ Jellyfin API integration with session monitoring
- ✅ Smart session restart mechanism for bandwidth changes
- ✅ Three bandwidth allocation algorithms (equal, priority, demand-based)
- ✅ Configurable IP range detection for external users
- ✅ Comprehensive logging and error handling
- ✅ Dry-run mode for safe testing
- ✅ Test suite for validation and debugging
- ✅ Real-world bandwidth control testing script

### Planned Features
- 🔄 User bandwidth usage monitoring
- 🔄 Historical bandwidth data collection
- 🔄 Web dashboard for monitoring and control
- 🔄 Advanced SQM integration
- 🔄 Notification system for bandwidth events

## Contributing

This project is designed to be easily extensible:

- **New algorithms**: Inherit from `BandwidthAlgorithm` class
- **Additional routers**: Create new client classes following the `OpenWRTClient` pattern
- **Enhanced monitoring**: Extend the logging and metrics collection

## License

MIT License - See LICENSE file for details 
