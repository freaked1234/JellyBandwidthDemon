#!/usr/bin/env python3
"""
JellyDemon - Intelligent Jellyfin Bandwidth Management Daemon

Main daemon script that coordinates bandwidth monitoring and management.
"""

import sys
import time
from collections import deque
import signal
import logging
import argparse
from pathlib import Path
import yaml
from typing import Dict, Any

from modules.config import Config
from modules.logger import setup_logging
from modules.openwrt_client import OpenWRTClient
from modules.jellyfin_client import JellyfinClient
from modules.bandwidth_manager import BandwidthManager
from modules.network_utils import NetworkUtils


class JellyDemon:
    """Main daemon class for bandwidth management."""
    
    def __init__(self, config_path: str = "config.yml"):
        """Initialize the daemon with configuration."""
        self.config = Config(config_path)
        self.logger = setup_logging(self.config)
        self.running = False
        
        # Initialize clients
        self.openwrt = OpenWRTClient(self.config.router)
        self.jellyfin = JellyfinClient(self.config.jellyfin)
        self.bandwidth_manager = BandwidthManager(self.config.bandwidth)
        self.network_utils = NetworkUtils(self.config.network)
        self.bandwidth_history = deque()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("JellyDemon initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def validate_connectivity(self) -> bool:
        """Validate connectivity to all required services."""
        self.logger.info("Validating connectivity...")
        
        # Test OpenWRT connection
        if not self.openwrt.test_connection():
            self.logger.error("Failed to connect to OpenWRT router")
            return False
        
        # Test Jellyfin connection
        if not self.jellyfin.test_connection():
            self.logger.error("Failed to connect to Jellyfin server")
            return False
        
        self.logger.info("All connectivity tests passed")
        return True
    
    def get_current_bandwidth_usage(self) -> float:
        """Get averaged upload bandwidth usage from router."""
        try:
            usage = self.openwrt.get_bandwidth_usage()

            if self.config.router.jellyfin_ip:
                jf_usage = self.openwrt.get_bandwidth_usage(self.config.router.jellyfin_ip)
                usage = max(usage - jf_usage, 0)
                self.logger.debug(
                    f"Subtracting Jellyfin traffic {jf_usage:.2f} Mbps from total"
                )

            now = time.time()
            self.bandwidth_history.append((now, usage))

            # Remove samples older than spike_duration window
            window = self.config.bandwidth.spike_duration * 60
            while self.bandwidth_history and now - self.bandwidth_history[0][0] > window:
                self.bandwidth_history.popleft()

            avg_usage = sum(u for _, u in self.bandwidth_history) / len(self.bandwidth_history)
            self.logger.debug(
                f"Current upload usage: {avg_usage:.2f} Mbps (raw {usage:.2f} Mbps)"
            )
            return avg_usage
        except Exception as e:
            self.logger.error(f"Failed to get bandwidth usage: {e}")
            return 0.0
    
    def get_external_streamers(self) -> Dict[str, Dict[str, Any]]:
        """Get list of users streaming from external IPs."""
        try:
            # Get active sessions from Jellyfin
            sessions = self.jellyfin.get_active_sessions()
            external_sessions = {}
            
            for session in sessions:
                user_id = session.get('UserId')
                remote_endpoint = session.get('RemoteEndPoint', '')
                
                if user_id and remote_endpoint:
                    # Extract IP from endpoint (format: "IP:PORT")
                    client_ip = remote_endpoint.split(':')[0]
                    
                    # Check if IP is external
                    if self.network_utils.is_external_ip(client_ip):
                        external_sessions[user_id] = {
                            'ip': client_ip,
                            'session_data': session,
                            'user_data': self.jellyfin.get_user_info(user_id)
                        }
                        self.logger.debug(f"External streamer found: {user_id} from {client_ip}")
            
            self.logger.info(f"Found {len(external_sessions)} external streamers")
            return external_sessions
            
        except Exception as e:
            self.logger.error(f"Failed to get external streamers: {e}")
            return {}
    
    def calculate_and_apply_limits(self, external_streamers: Dict[str, Dict[str, Any]], 
                                  current_usage: float):
        """Calculate and apply bandwidth limits for external users."""
        if not external_streamers:
            self.logger.debug("No external streamers, skipping bandwidth calculation")
            return
        
        try:
            # Calculate available bandwidth
            total_bandwidth = self.config.bandwidth.total_upload_mbps
            if total_bandwidth == 0:
                total_bandwidth = self.openwrt.get_total_bandwidth()
            
            available_bandwidth = total_bandwidth - current_usage - self.config.bandwidth.reserved_bandwidth
            
            self.logger.info(f"Total: {total_bandwidth:.2f} Mbps, "
                           f"Current usage: {current_usage:.2f} Mbps, "
                           f"Available: {available_bandwidth:.2f} Mbps")
            
            # Calculate per-user limits
            user_limits = self.bandwidth_manager.calculate_limits(
                external_streamers, available_bandwidth
            )
            
            # Apply limits to Jellyfin users
            for user_id, limit in user_limits.items():
                if self.config.daemon.dry_run:
                    self.logger.info(
                        f"[DRY RUN] Would set user {user_id} limit to {limit:.2f} Mbps"
                    )
                    continue

                changed = self.jellyfin.set_user_bandwidth_limit(user_id, limit)
                self.logger.info(
                    f"Set user {user_id} bandwidth limit to {limit:.2f} Mbps"
                )

                if changed:
                    session = external_streamers.get(user_id, {}).get('session_data')
                    if session and session.get('NowPlayingItem'):
                        self.jellyfin.restart_stream(session)
                    
        except Exception as e:
            self.logger.error(f"Failed to calculate/apply limits: {e}")
    
    def run_single_cycle(self):
        """Run a single monitoring/adjustment cycle."""
        self.logger.debug("Starting monitoring cycle")
        
        # Get current bandwidth usage
        current_usage = self.get_current_bandwidth_usage()
        
        # Get external streamers
        external_streamers = self.get_external_streamers()
        
        # Calculate and apply bandwidth limits
        self.calculate_and_apply_limits(external_streamers, current_usage)
        
        self.logger.debug("Monitoring cycle completed")
    
    def run(self):
        """Main daemon loop."""
        if not self.validate_connectivity():
            self.logger.error("Connectivity validation failed, exiting")
            return 1
        
        self.logger.info("Starting JellyDemon main loop")
        self.running = True
        
        try:
            while self.running:
                self.run_single_cycle()
                
                # Sleep for configured interval
                for _ in range(self.config.daemon.update_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
            return 1
        
        finally:
            self.logger.info("JellyDemon shutting down")
            # TODO: Restore original user settings if backup was enabled
        
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="JellyDemon - Jellyfin Bandwidth Manager")
    parser.add_argument("--config", "-c", default="config.yml", 
                       help="Configuration file path")
    parser.add_argument("--dry-run", action="store_true",
                       help="Run in dry-run mode (no changes applied)")
    parser.add_argument("--test", action="store_true",
                       help="Test connectivity and exit")
    
    args = parser.parse_args()
    
    try:
        daemon = JellyDemon(args.config)
        
        # Override dry-run setting if specified
        if args.dry_run:
            daemon.config.daemon.dry_run = True
        
        if args.test:
            # Test mode - just validate connectivity
            if daemon.validate_connectivity():
                print("✓ All connectivity tests passed")
                return 0
            else:
                print("✗ Connectivity tests failed")
                return 1
        
        # Run the daemon
        return daemon.run()
        
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 