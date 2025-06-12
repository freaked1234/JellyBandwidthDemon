"""
OpenWRT router client for bandwidth monitoring and SQM control.
"""

import requests
import subprocess
import json
import logging
import paramiko
from typing import Dict, Any, Optional, TYPE_CHECKING
from urllib.parse import urljoin

if TYPE_CHECKING:
    from .config import RouterConfig


class OpenWRTClient:
    """Client for communicating with OpenWRT router."""
    
    def __init__(self, config: 'RouterConfig'):
        """Initialize the OpenWRT client."""
        self.config = config
        self.logger = logging.getLogger('jellydemon.openwrt')
        self.session = requests.Session()
        self.ssh_client = None
        
        # Setup session with timeout
        self.session.timeout = 10
        
        # LuCI endpoints
        self.luci_base = f"http://{config.host}:{config.luci_port}"
        self.auth_token = None
    
    def test_connection(self) -> bool:
        """Test connection to the router."""
        try:
            if self.config.use_ssh:
                return self._test_ssh_connection()
            else:
                return self._test_luci_connection()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def _test_ssh_connection(self) -> bool:
        """Test SSH connection to router."""
        try:
            if self.ssh_client is None:
                self._connect_ssh()
            
            # Test command execution
            stdin, stdout, stderr = self.ssh_client.exec_command('echo "test"')
            result = stdout.read().decode().strip()
            return result == "test"
            
        except Exception as e:
            self.logger.error(f"SSH connection test failed: {e}")
            return False
    
    def _test_luci_connection(self) -> bool:
        """Test LuCI web interface connection."""
        try:
            response = self.session.get(f"{self.luci_base}/cgi-bin/luci")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"LuCI connection test failed: {e}")
            return False
    
    def _connect_ssh(self):
        """Establish SSH connection to router."""
        if self.ssh_client is not None:
            return
        
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        self.ssh_client.connect(
            hostname=self.config.host,
            port=self.config.ssh_port,
            username=self.config.username,
            password=self.config.password,
            timeout=10
        )
        self.logger.debug("SSH connection established")
    
    def _authenticate_luci(self) -> bool:
        """Authenticate with LuCI interface."""
        if self.auth_token:
            return True
        
        try:
            # Get login page to retrieve token
            login_url = f"{self.luci_base}/cgi-bin/luci"
            response = self.session.get(login_url)
            
            # Extract token from response (this may need adjustment based on LuCI version)
            # For now, we'll try a basic authentication approach
            auth_data = {
                'luci_username': self.config.username,
                'luci_password': self.config.password
            }
            
            auth_response = self.session.post(login_url, data=auth_data)
            
            if auth_response.status_code == 200:
                self.auth_token = True  # Simplified for now
                self.logger.debug("LuCI authentication successful")
                return True
            else:
                self.logger.error(f"LuCI authentication failed: {auth_response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"LuCI authentication error: {e}")
            return False
    
    def get_bandwidth_usage(self, ip: Optional[str] = None) -> float:
        """
        Get upload bandwidth usage in Mbps. If ``ip`` is provided, return
        usage specific to that IP address using either SSH or LuCI.

        Args:
            ip: Optional IP address to query

        Returns:
            Current upload bandwidth usage in Mbps
        """
        try:
            if self.config.use_ssh:
                return self._get_bandwidth_usage_ssh(ip)
            else:
                return self._get_bandwidth_usage_luci(ip)
        except Exception as e:
            self.logger.error(f"Failed to get bandwidth usage: {e}")
            return 0.0

    def _get_bandwidth_usage_ssh(self, ip: Optional[str] = None) -> float:
        """Get bandwidth usage via SSH."""
        if self.ssh_client is None:
            self._connect_ssh()

        if ip:
            cmd = f"""
            BYTES1=$(iptables -nvx -L FORWARD | awk '$8 == "{ip}" {{sum+=$2}} END {{print sum}}')
            sleep 1
            BYTES2=$(iptables -nvx -L FORWARD | awk '$8 == "{ip}" {{sum+=$2}} END {{print sum}}')
            BPS=$((BYTES2 - BYTES1))
            echo "scale=2; $BPS * 8 / 1000000" | bc -l
            """
        else:
            cmd = """
            WAN_IF=$(uci get network.wan.device 2>/dev/null || echo "eth0")
            TX_BYTES=$(cat /sys/class/net/$WAN_IF/statistics/tx_bytes 2>/dev/null || echo "0")
            sleep 1
            TX_BYTES2=$(cat /sys/class/net/$WAN_IF/statistics/tx_bytes 2>/dev/null || echo "0")
            BPS=$((TX_BYTES2 - TX_BYTES))
            echo "scale=2; $BPS * 8 / 1000000" | bc -l
            """

        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        result = stdout.read().decode().strip()

        try:
            mbps = float(result)
            self.logger.debug(f"Current upload usage: {mbps:.2f} Mbps")
            return mbps
        except ValueError:
            self.logger.error(f"Invalid bandwidth reading: {result}")
            return 0.0

    def _get_bandwidth_usage_luci(self, ip: Optional[str] = None) -> float:
        """Get bandwidth usage via LuCI API."""
        if not self._authenticate_luci():
            return 0.0

        try:
            # LuCI RPC call for network statistics
            # This endpoint may vary depending on LuCI version
            if ip:
                stats_url = f"{self.luci_base}/cgi-bin/luci/admin/status/realtime/bandwidth?ip={ip}"
            else:
                stats_url = f"{self.luci_base}/cgi-bin/luci/admin/status/realtime/bandwidth"
            response = self.session.get(stats_url)

            if response.status_code == 200:
                data = response.json()
                # Extract upload bandwidth from response
                # This will need to be adjusted based on actual LuCI response format
                upload_mbps = data.get('upload_mbps', 0.0)
                return upload_mbps
            else:
                self.logger.error(f"LuCI bandwidth query failed: {response.status_code}")
                return 0.0
                
        except Exception as e:
            self.logger.error(f"LuCI bandwidth query error: {e}")
            return 0.0
    
    def get_total_bandwidth(self) -> float:
        """
        Get total upload bandwidth capacity in Mbps.
        
        Returns:
            Total upload bandwidth capacity in Mbps
        """
        try:
            if self.config.use_ssh:
                return self._get_total_bandwidth_ssh()
            else:
                return self._get_total_bandwidth_luci()
        except Exception as e:
            self.logger.error(f"Failed to get total bandwidth: {e}")
            return 100.0  # Default fallback
    
    def _get_total_bandwidth_ssh(self) -> float:
        """Get total bandwidth capacity via SSH."""
        if self.ssh_client is None:
            self._connect_ssh()
        
        # Try to get upload speed from SQM configuration
        cmd = """
        # Check SQM upload rate
        SQM_UPLOAD=$(uci get sqm.@queue[0].upload 2>/dev/null || echo "0")
        if [ "$SQM_UPLOAD" != "0" ]; then
            # Convert kbits to Mbps
            echo "scale=2; $SQM_UPLOAD / 1000" | bc -l
        else
            # Try to get from network configuration or default
            echo "100"  # Default 100 Mbps
        fi
        """
        
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        result = stdout.read().decode().strip()
        
        try:
            mbps = float(result)
            self.logger.debug(f"Total upload capacity: {mbps:.2f} Mbps")
            return mbps
        except ValueError:
            self.logger.error(f"Invalid total bandwidth reading: {result}")
            return 100.0
    
    def _get_total_bandwidth_luci(self) -> float:
        """Get total bandwidth capacity via LuCI API."""
        # This would need implementation based on LuCI API
        # For now, return a default value
        return 100.0
    
    def get_sqm_settings(self) -> Dict[str, Any]:
        """Get current SQM (Smart Queue Management) settings."""
        if not self.config.use_ssh:
            self.logger.warning("SQM settings retrieval requires SSH access")
            return {}
        
        try:
            if self.ssh_client is None:
                self._connect_ssh()
            
            cmd = "uci show sqm"
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
            result = stdout.read().decode()
            
            # Parse UCI output into dictionary
            settings = {}
            for line in result.split('\n'):
                if '=' in line and line.startswith('sqm.'):
                    key, value = line.split('=', 1)
                    settings[key] = value.strip("'\"")
            
            return settings
            
        except Exception as e:
            self.logger.error(f"Failed to get SQM settings: {e}")
            return {}
    
    def set_sqm_upload_rate(self, rate_kbps: int) -> bool:
        """
        Set SQM upload rate limit.
        
        Args:
            rate_kbps: Upload rate in kbps
            
        Returns:
            True if successful, False otherwise
        """
        if not self.config.use_ssh:
            self.logger.warning("SQM configuration requires SSH access")
            return False
        
        try:
            if self.ssh_client is None:
                self._connect_ssh()
            
            # Update SQM configuration
            cmd = f"""
            uci set sqm.@queue[0].upload={rate_kbps}
            uci commit sqm
            /etc/init.d/sqm restart
            """
            
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
            error_output = stderr.read().decode()
            
            if error_output:
                self.logger.error(f"SQM configuration error: {error_output}")
                return False
            
            self.logger.info(f"SQM upload rate set to {rate_kbps} kbps")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set SQM upload rate: {e}")
            return False
    
    def __del__(self):
        """Clean up connections."""
        if self.ssh_client:
            self.ssh_client.close() 