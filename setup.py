#!/usr/bin/env python3
"""
Setup script for JellyDemon - Jellyfin Bandwidth Management Daemon
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def install_dependencies():
    """Install Python dependencies."""
    print("Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False


def create_config():
    """Create configuration file from example."""
    config_file = Path("config.yml")
    example_file = Path("config.example.yml")
    
    if config_file.exists():
        print("✓ Configuration file already exists")
        return True
    
    if not example_file.exists():
        print("✗ Example configuration file not found")
        return False
    
    try:
        shutil.copy(example_file, config_file)
        print("✓ Created config.yml from example")
        print("  Please edit config.yml with your specific settings")
        return True
    except Exception as e:
        print(f"✗ Failed to create config file: {e}")
        return False


def create_systemd_service():
    """Create systemd service file."""
    service_content = f"""[Unit]
Description=JellyDemon - Jellyfin Bandwidth Management Daemon
After=network.target

[Service]
Type=simple
User=jellydemon
Group=jellydemon
WorkingDirectory={Path.cwd()}
ExecStart={sys.executable} {Path.cwd() / 'jellydemon.py'}
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={Path.cwd()}

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path("/etc/systemd/system/jellydemon.service")
    
    try:
        # Check if we have write permission
        if os.access("/etc/systemd/system", os.W_OK):
            with open(service_file, 'w') as f:
                f.write(service_content)
            print("✓ Created systemd service file")
            print("  Run 'sudo systemctl enable jellydemon' to enable auto-start")
            return True
        else:
            # Write to local directory
            local_service = Path("jellydemon.service")
            with open(local_service, 'w') as f:
                f.write(service_content)
            print("✓ Created jellydemon.service in current directory")
            print("  Copy to /etc/systemd/system/ with: sudo cp jellydemon.service /etc/systemd/system/")
            return True
            
    except Exception as e:
        print(f"✗ Failed to create service file: {e}")
        return False


def test_connectivity():
    """Test basic connectivity."""
    print("Testing basic connectivity...")
    
    try:
        # Test if we can import our modules
        from modules.config import Config
        from modules.jellyfin_client import JellyfinClient
        from modules.openwrt_client import OpenWRTClient
        print("✓ All modules imported successfully")
        
        # Try to load config
        if Path("config.yml").exists():
            try:
                config = Config("config.yml")
                print("✓ Configuration loaded successfully")
            except Exception as e:
                print(f"⚠ Configuration has issues: {e}")
                print("  Please review and fix config.yml")
        else:
            print("⚠ No config.yml found - please create and configure it")
        
        return True
        
    except ImportError as e:
        print(f"✗ Module import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def main():
    """Main setup function."""
    print("JellyDemon Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version.split()[0]} detected")
    
    success = True
    
    # Install dependencies
    if not install_dependencies():
        success = False
    
    # Create config
    if not create_config():
        success = False
    
    # Create systemd service
    if not create_systemd_service():
        success = False
    
    # Test connectivity
    if not test_connectivity():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit config.yml with your router and Jellyfin settings")
        print("2. Test connectivity: python jellydemon.py --test")
        print("3. Run in dry-run mode: python jellydemon.py --dry-run")
        print("4. Run normally: python jellydemon.py")
    else:
        print("⚠ Setup completed with warnings")
        print("Please review the issues above before running JellyDemon")


if __name__ == "__main__":
    main() 