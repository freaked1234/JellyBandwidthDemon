# JellyDemon - Intelligent Jellyfin Bandwidth Management

A Python daemon that automatically manages Jellyfin user bandwidth limits based on real-time network demand and external streaming activity.

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
- **Configurable Algorithms**: Pluggable bandwidth calculation formulas
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Safe Operation**: Validates changes before applying to prevent service disruption

## Requirements

- OpenWRT router with LuCI/SSH access
- Jellyfin server with API access
- Python 3.8+ environment (recommended: separate LXC container)
- Network access to both router and Jellyfin server

## Installation

### Quick Setup

```bash
# 1. Clone/download this project to your target machine
git clone <repository-url> jellydemon
cd jellydemon

# 2. Run the setup script
python setup.py

# 3. Edit configuration with your specific settings
nano config.yml

# 4. Test connectivity
python jellydemon.py --test

# 5. Run in dry-run mode first
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

3. **Configure your settings:**
   - **Router settings**: Update with your GL-MT6000 IP and credentials
   - **Jellyfin settings**: Add your server URL and API key
   - **Network ranges**: Configure your internal IP ranges
   - **Bandwidth settings**: Adjust limits and algorithm preferences

4. **Get Jellyfin API Key:**
   - Go to Jellyfin Admin Dashboard → API Keys
   - Create a new API key for JellyDemon
   - Copy the key to your config.yml

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

Key configuration options in `config.yml`:

- **Router settings**: IP, authentication, API endpoints
- **Jellyfin settings**: URL, API key, user management
- **Network ranges**: Define internal/external IP ranges
- **Bandwidth algorithms**: Select calculation method
- **Daemon settings**: Update intervals, logging level

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

# Check logs
tail -f jellydemon.log
```

## OpenWRT Router Configuration

For optimal compatibility with your GL-MT6000:

1. **Enable SSH access** (if using SSH method):
   ```bash
   # On router
   uci set dropbear.@dropbear[0].PasswordAuth='on'
   uci commit dropbear
   /etc/init.d/dropbear restart
   ```

2. **Install required packages** (SSH method):
   ```bash
   # On router
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
   
   # Test Jellyfin API
   curl -H "Authorization: MediaBrowser Token=YOUR_API_KEY" \
        http://your-jellyfin:8096/System/Info
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
- ✅ Three bandwidth allocation algorithms (equal, priority, demand-based)
- ✅ Configurable IP range detection for external users
- ✅ Comprehensive logging and error handling
- ✅ Dry-run mode for safe testing
- ✅ Test suite for validation and debugging

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