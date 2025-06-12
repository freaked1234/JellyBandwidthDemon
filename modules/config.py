"""
Configuration management for JellyDemon.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class RouterConfig:
    """Router configuration settings."""
    host: str
    username: str
    password: str
    ssh_port: int = 22
    luci_port: int = 80
    use_ssh: bool = False


@dataclass
class JellyfinConfig:
    """Jellyfin configuration settings."""
    host: str
    port: int
    api_key: str
    use_https: bool = False
    
    @property
    def base_url(self) -> str:
        """Get the base URL for Jellyfin API."""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.host}:{self.port}"


@dataclass
class NetworkConfig:
    """Network configuration settings."""
    internal_ranges: List[str]
    test_mode: bool = False
    test_external_ranges: List[str] = None


@dataclass
class BandwidthConfig:
    """Bandwidth management configuration."""
    algorithm: str = "equal_split"
    min_per_user: float = 2.0
    max_per_user: float = 50.0
    reserved_bandwidth: float = 10.0
    total_upload_mbps: float = 0
    spike_duration: int = 3  # minutes to average usage over


@dataclass
class DaemonConfig:
    """Daemon operation configuration."""
    update_interval: int = 30
    log_level: str = "INFO"
    log_file: str = "jellydemon.log"
    log_max_size: str = "10MB"
    log_backup_count: int = 5
    dry_run: bool = False
    backup_user_settings: bool = True
    pid_file: str = "/tmp/jellydemon.pid"


class Config:
    """Main configuration class."""
    
    def __init__(self, config_path: str = "config.yml"):
        """Load configuration from YAML file."""
        self.config_path = Path(config_path)
        self._load_config()
    
    def _load_config(self):
        """Load and parse configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Parse configuration sections
        self.router = RouterConfig(**config_data.get('router', {}))
        self.jellyfin = JellyfinConfig(**config_data.get('jellyfin', {}))
        self.network = NetworkConfig(**config_data.get('network', {}))
        self.bandwidth = BandwidthConfig(**config_data.get('bandwidth', {}))
        self.daemon = DaemonConfig(**config_data.get('daemon', {}))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values."""
        # Validate router config
        if not self.router.host:
            raise ValueError("Router host is required")
        
        # Validate Jellyfin config
        if not self.jellyfin.host:
            raise ValueError("Jellyfin host is required")
        if not self.jellyfin.api_key:
            raise ValueError("Jellyfin API key is required")
        
        # Validate network config
        if not self.network.internal_ranges:
            raise ValueError("At least one internal IP range is required")
        
        # Validate bandwidth config
        if self.bandwidth.min_per_user >= self.bandwidth.max_per_user:
            raise ValueError("min_per_user must be less than max_per_user")
        if self.bandwidth.spike_duration <= 0:
            raise ValueError("spike_duration must be greater than zero")
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config() 