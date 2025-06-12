"""
Jellyfin client for session monitoring and user bandwidth management.
"""

import requests
import json
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from urllib.parse import urljoin

if TYPE_CHECKING:
    from .config import JellyfinConfig


class JellyfinClient:
    """Client for communicating with Jellyfin server."""
    
    def __init__(self, config: 'JellyfinConfig'):
        """Initialize the Jellyfin client."""
        self.config = config
        self.logger = logging.getLogger('jellydemon.jellyfin')
        self.session = requests.Session()
        
        # Setup session
        self.session.timeout = 30
        self.session.headers.update({
            'Authorization': f'MediaBrowser Token={config.api_key}',
            'Content-Type': 'application/json'
        })
        
        # Cache for user data
        self._user_cache = {}
        self._original_user_settings = {}
    
    def test_connection(self) -> bool:
        """Test connection to Jellyfin server."""
        try:
            url = urljoin(self.config.base_url, '/System/Info')
            response = self.session.get(url)
            
            if response.status_code == 200:
                info = response.json()
                self.logger.debug(f"Connected to Jellyfin {info.get('Version', 'unknown')}")
                return True
            else:
                self.logger.error(f"Jellyfin connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Jellyfin connection test failed: {e}")
            return False
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get list of active streaming sessions.
        
        Returns:
            List of active session objects
        """
        try:
            url = urljoin(self.config.base_url, '/Sessions')
            response = self.session.get(url)
            
            if response.status_code == 200:
                sessions = response.json()
                
                # Filter for active streaming sessions
                active_sessions = []
                for session in sessions:
                    # Check if session is actively streaming
                    if (session.get('NowPlayingItem') and 
                        session.get('PlayState', {}).get('IsPaused', True) is False):
                        active_sessions.append(session)
                
                self.logger.debug(f"Found {len(active_sessions)} active streaming sessions")
                return active_sessions
            else:
                self.logger.error(f"Failed to get sessions: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting active sessions: {e}")
            return []
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by user ID.
        
        Args:
            user_id: Jellyfin user ID
            
        Returns:
            User information dictionary or None
        """
        # Check cache first
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        try:
            url = urljoin(self.config.base_url, f'/Users/{user_id}')
            response = self.session.get(url)
            
            if response.status_code == 200:
                user_info = response.json()
                self._user_cache[user_id] = user_info
                return user_info
            else:
                self.logger.error(f"Failed to get user info for {user_id}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting user info for {user_id}: {e}")
            return None
    
    def get_user_policy(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user policy settings.
        
        Args:
            user_id: Jellyfin user ID
            
        Returns:
            User policy dictionary or None
        """
        try:
            url = urljoin(self.config.base_url, f'/Users/{user_id}/Policy')
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get user policy for {user_id}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting user policy for {user_id}: {e}")
            return None
    
    def set_user_bandwidth_limit(self, user_id: str, limit_mbps: float) -> bool:
        """
        Set bandwidth limit for a user.
        
        Args:
            user_id: Jellyfin user ID
            limit_mbps: Bandwidth limit in Mbps
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current user policy
            policy = self.get_user_policy(user_id)
            if not policy:
                self.logger.error(f"Could not get policy for user {user_id}")
                return False
            
            # Backup original settings if not already done
            if user_id not in self._original_user_settings:
                self._original_user_settings[user_id] = {
                    'RemoteClientBitrateLimit': policy.get('RemoteClientBitrateLimit', 0)
                }
            
            # Convert Mbps to bits per second (Jellyfin uses bps)
            limit_bps = int(limit_mbps * 1_000_000)
            
            # Update policy
            policy['RemoteClientBitrateLimit'] = limit_bps
            
            # Apply updated policy
            url = urljoin(self.config.base_url, f'/Users/{user_id}/Policy')
            response = self.session.post(url, json=policy)
            
            if response.status_code == 204:  # No Content = Success
                user_info = self.get_user_info(user_id)
                username = user_info.get('Name', user_id) if user_info else user_id
                self.logger.info(f"Set bandwidth limit for user {username} to {limit_mbps:.2f} Mbps")
                return True
            else:
                self.logger.error(f"Failed to set bandwidth limit for {user_id}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting bandwidth limit for {user_id}: {e}")
            return False
    
    def restore_user_bandwidth_limits(self) -> bool:
        """
        Restore original bandwidth limits for all modified users.
        
        Returns:
            True if all restorations successful, False otherwise
        """
        success = True
        
        for user_id, original_settings in self._original_user_settings.items():
            try:
                policy = self.get_user_policy(user_id)
                if policy:
                    policy['RemoteClientBitrateLimit'] = original_settings['RemoteClientBitrateLimit']
                    
                    url = urljoin(self.config.base_url, f'/Users/{user_id}/Policy')
                    response = self.session.post(url, json=policy)
                    
                    if response.status_code == 204:
                        user_info = self.get_user_info(user_id)
                        username = user_info.get('Name', user_id) if user_info else user_id
                        self.logger.info(f"Restored original bandwidth limit for user {username}")
                    else:
                        self.logger.error(f"Failed to restore bandwidth limit for {user_id}: {response.status_code}")
                        success = False
                        
            except Exception as e:
                self.logger.error(f"Error restoring bandwidth limit for {user_id}: {e}")
                success = False
        
        return success
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session information dictionary or None
        """
        try:
            url = urljoin(self.config.base_url, f'/Sessions/{session_id}')
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get session info for {session_id}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting session info for {session_id}: {e}")
            return None
    
    def get_user_bandwidth_usage(self, user_id: str) -> float:
        """
        Get current bandwidth usage for a user (estimated from active sessions).
        
        Args:
            user_id: Jellyfin user ID
            
        Returns:
            Estimated bandwidth usage in Mbps
        """
        try:
            sessions = self.get_active_sessions()
            total_bitrate = 0
            
            for session in sessions:
                if session.get('UserId') == user_id:
                    # Try to get bitrate from transcoding info or stream info
                    transcoding_info = session.get('TranscodingInfo', {})
                    if transcoding_info:
                        bitrate = transcoding_info.get('Bitrate', 0)
                        if bitrate:
                            total_bitrate += bitrate
                    else:
                        # Estimate based on media info
                        now_playing = session.get('NowPlayingItem', {})
                        bitrate = now_playing.get('Bitrate', 5_000_000)  # Default 5 Mbps
                        total_bitrate += bitrate
            
            # Convert from bps to Mbps
            return total_bitrate / 1_000_000
            
        except Exception as e:
            self.logger.error(f"Error getting bandwidth usage for {user_id}: {e}")
            return 0.0
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Get list of all users.
        
        Returns:
            List of user objects
        """
        try:
            url = urljoin(self.config.base_url, '/Users')
            response = self.session.get(url)
            
            if response.status_code == 200:
                users = response.json()
                self.logger.debug(f"Retrieved {len(users)} users")
                return users
            else:
                self.logger.error(f"Failed to get users: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting users: {e}")
            return []
    
    def clear_user_cache(self):
        """Clear the user information cache."""
        self._user_cache.clear()
        self.logger.debug("User cache cleared") 