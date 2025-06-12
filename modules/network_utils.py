"""
Network utilities for IP range checking and validation.
"""

import ipaddress
import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import NetworkConfig


class NetworkUtils:
    """Utilities for network operations and IP validation."""
    
    def __init__(self, config: 'NetworkConfig'):
        """Initialize with network configuration."""
        self.config = config
        self.logger = logging.getLogger('jellydemon.network')
        
        # Parse IP ranges
        self.internal_networks = []
        for range_str in config.internal_ranges:
            try:
                network = ipaddress.ip_network(range_str, strict=False)
                self.internal_networks.append(network)
                self.logger.debug(f"Added internal network range: {network}")
            except ValueError as e:
                self.logger.error(f"Invalid IP range '{range_str}': {e}")
        
        # Parse test external ranges if in test mode
        self.test_external_networks = []
        if config.test_mode and config.test_external_ranges:
            for range_str in config.test_external_ranges:
                try:
                    network = ipaddress.ip_network(range_str, strict=False)
                    self.test_external_networks.append(network)
                    self.logger.debug(f"Added test external network range: {network}")
                except ValueError as e:
                    self.logger.error(f"Invalid test IP range '{range_str}': {e}")
    
    def is_external_ip(self, ip_str: str) -> bool:
        """
        Check if an IP address is considered external.
        
        Args:
            ip_str: IP address as string
            
        Returns:
            True if the IP is considered external, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            
            # In test mode, check test external ranges first
            if self.config.test_mode and self.test_external_networks:
                for network in self.test_external_networks:
                    if ip in network:
                        self.logger.debug(f"IP {ip_str} matches test external range {network}")
                        return True
                # If test mode but IP doesn't match test ranges, consider it internal
                return False
            
            # Normal operation: check if IP is NOT in internal ranges
            for network in self.internal_networks:
                if ip in network:
                    self.logger.debug(f"IP {ip_str} is internal (matches {network})")
                    return False
            
            self.logger.debug(f"IP {ip_str} is external")
            return True
            
        except ValueError as e:
            self.logger.error(f"Invalid IP address '{ip_str}': {e}")
            return False
    
    def is_valid_ip(self, ip_str: str) -> bool:
        """Check if a string represents a valid IP address."""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
    
    def get_network_info(self, ip_str: str) -> dict:
        """Get detailed network information for an IP address."""
        try:
            ip = ipaddress.ip_address(ip_str)
            info = {
                'ip': str(ip),
                'version': ip.version,
                'is_private': ip.is_private,
                'is_loopback': ip.is_loopback,
                'is_multicast': ip.is_multicast,
                'is_external': self.is_external_ip(ip_str)
            }
            
            # Find matching internal network
            for network in self.internal_networks:
                if ip in network:
                    info['internal_network'] = str(network)
                    break
            
            return info
            
        except ValueError as e:
            return {'error': str(e)} 