"""
Bandwidth management algorithms and calculations.
"""

import logging
from typing import Dict, Any, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .config import BandwidthConfig


class BandwidthAlgorithm(ABC):
    """Abstract base class for bandwidth calculation algorithms."""
    
    @abstractmethod
    def calculate_limits(self, external_streamers: Dict[str, Dict[str, Any]], 
                        available_bandwidth: float, config: 'BandwidthConfig') -> Dict[str, float]:
        """
        Calculate bandwidth limits for external users.
        
        Args:
            external_streamers: Dictionary of external streaming users
            available_bandwidth: Available bandwidth in Mbps
            config: Bandwidth configuration
            
        Returns:
            Dictionary mapping user_id to bandwidth limit in Mbps
        """
        pass


class EqualSplitAlgorithm(BandwidthAlgorithm):
    """Equal split algorithm - divide available bandwidth equally among users."""
    
    def calculate_limits(self, external_streamers: Dict[str, Dict[str, Any]], 
                        available_bandwidth: float, config: 'BandwidthConfig') -> Dict[str, float]:
        """Divide available bandwidth equally among all external users."""
        if not external_streamers or available_bandwidth <= 0:
            return {}
        
        num_users = len(external_streamers)
        per_user_bandwidth = available_bandwidth / num_users
        
        # Apply min/max constraints
        per_user_bandwidth = max(config.min_per_user, per_user_bandwidth)
        per_user_bandwidth = min(config.max_per_user, per_user_bandwidth)
        
        return {user_id: per_user_bandwidth for user_id in external_streamers.keys()}


class PriorityBasedAlgorithm(BandwidthAlgorithm):
    """Priority-based algorithm - allocate based on user priority levels."""
    
    def calculate_limits(self, external_streamers: Dict[str, Dict[str, Any]], 
                        available_bandwidth: float, config: 'BandwidthConfig') -> Dict[str, float]:
        """
        Allocate bandwidth based on user priority.
        
        Priority levels (from user policy):
        - Admin users get highest priority
        - Premium users get medium priority  
        - Regular users get standard priority
        """
        if not external_streamers or available_bandwidth <= 0:
            return {}
        
        # Categorize users by priority
        admin_users = []
        premium_users = []
        regular_users = []
        
        for user_id, user_data in external_streamers.items():
            user_info = user_data.get('user_data', {})
            policy = user_info.get('Policy', {})
            
            if policy.get('IsAdministrator', False):
                admin_users.append(user_id)
            elif policy.get('IsDisabled', False) is False and policy.get('EnableAllFolders', False):
                premium_users.append(user_id)
            else:
                regular_users.append(user_id)
        
        # Allocation ratios (admin:premium:regular = 3:2:1)
        admin_ratio = 3.0
        premium_ratio = 2.0
        regular_ratio = 1.0
        
        total_weight = (len(admin_users) * admin_ratio + 
                       len(premium_users) * premium_ratio + 
                       len(regular_users) * regular_ratio)
        
        if total_weight == 0:
            return {}
        
        # Calculate bandwidth per weight unit
        bandwidth_per_unit = available_bandwidth / total_weight
        
        user_limits = {}
        
        # Assign bandwidth based on priority
        for user_id in admin_users:
            limit = bandwidth_per_unit * admin_ratio
            limit = max(config.min_per_user, min(config.max_per_user, limit))
            user_limits[user_id] = limit
        
        for user_id in premium_users:
            limit = bandwidth_per_unit * premium_ratio
            limit = max(config.min_per_user, min(config.max_per_user, limit))
            user_limits[user_id] = limit
        
        for user_id in regular_users:
            limit = bandwidth_per_unit * regular_ratio
            limit = max(config.min_per_user, min(config.max_per_user, limit))
            user_limits[user_id] = limit
        
        return user_limits


class DemandBasedAlgorithm(BandwidthAlgorithm):
    """Demand-based algorithm - allocate based on current stream requirements."""
    
    def calculate_limits(self, external_streamers: Dict[str, Dict[str, Any]], 
                        available_bandwidth: float, config: 'BandwidthConfig') -> Dict[str, float]:
        """
        Allocate bandwidth based on actual stream demand.
        
        This algorithm tries to estimate required bandwidth based on:
        - Media bitrate
        - Transcoding requirements
        - Stream quality
        """
        if not external_streamers or available_bandwidth <= 0:
            return {}
        
        # Calculate required bandwidth for each user
        user_demands = {}
        total_demand = 0
        
        for user_id, user_data in external_streamers.items():
            session_data = user_data.get('session_data', {})
            demand = self._estimate_required_bandwidth(session_data)
            user_demands[user_id] = demand
            total_demand += demand
        
        # If total demand is within available bandwidth, allocate as demanded
        if total_demand <= available_bandwidth:
            user_limits = {}
            for user_id, demand in user_demands.items():
                limit = max(config.min_per_user, min(config.max_per_user, demand))
                user_limits[user_id] = limit
            return user_limits
        
        # If demand exceeds available bandwidth, scale proportionally
        scale_factor = available_bandwidth / total_demand
        user_limits = {}
        
        for user_id, demand in user_demands.items():
            scaled_limit = demand * scale_factor
            limit = max(config.min_per_user, min(config.max_per_user, scaled_limit))
            user_limits[user_id] = limit
        
        return user_limits
    
    def _estimate_required_bandwidth(self, session_data: Dict[str, Any]) -> float:
        """
        Estimate required bandwidth for a session.
        
        Args:
            session_data: Jellyfin session data
            
        Returns:
            Estimated bandwidth requirement in Mbps
        """
        # Check if transcoding is active
        transcoding_info = session_data.get('TranscodingInfo', {})
        if transcoding_info:
            # Use transcoding bitrate if available
            bitrate = transcoding_info.get('Bitrate', 0)
            if bitrate > 0:
                return bitrate / 1_000_000  # Convert to Mbps
        
        # Check media item bitrate
        now_playing = session_data.get('NowPlayingItem', {})
        media_bitrate = now_playing.get('Bitrate', 0)
        if media_bitrate > 0:
            return media_bitrate / 1_000_000  # Convert to Mbps
        
        # Estimate based on resolution/quality
        video_stream = None
        media_streams = now_playing.get('MediaStreams', [])
        for stream in media_streams:
            if stream.get('Type') == 'Video':
                video_stream = stream
                break
        
        if video_stream:
            width = video_stream.get('Width', 0)
            height = video_stream.get('Height', 0)
            
            # Rough estimates based on resolution
            if height >= 2160:  # 4K
                return 25.0
            elif height >= 1080:  # 1080p
                return 10.0
            elif height >= 720:  # 720p
                return 5.0
            else:  # SD
                return 3.0
        
        # Default estimate
        return 5.0  # 5 Mbps default


class BandwidthManager:
    """Manager for bandwidth calculation and allocation."""
    
    def __init__(self, config: 'BandwidthConfig'):
        """Initialize bandwidth manager."""
        self.config = config
        self.logger = logging.getLogger('jellydemon.bandwidth')
        
        # Initialize algorithm
        self.algorithm = self._create_algorithm(config.algorithm)
    
    def _create_algorithm(self, algorithm_name: str) -> BandwidthAlgorithm:
        """Create bandwidth algorithm instance."""
        algorithms = {
            'equal_split': EqualSplitAlgorithm,
            'priority_based': PriorityBasedAlgorithm,
            'demand_based': DemandBasedAlgorithm
        }
        
        algorithm_class = algorithms.get(algorithm_name)
        if not algorithm_class:
            self.logger.warning(f"Unknown algorithm '{algorithm_name}', falling back to equal_split")
            algorithm_class = EqualSplitAlgorithm
        
        self.logger.debug(f"Using bandwidth algorithm: {algorithm_class.__name__}")
        return algorithm_class()
    
    def calculate_limits(self, external_streamers: Dict[str, Dict[str, Any]], 
                        available_bandwidth: float) -> Dict[str, float]:
        """
        Calculate bandwidth limits for external users.
        
        Args:
            external_streamers: Dictionary of external streaming users
            available_bandwidth: Available bandwidth in Mbps
            
        Returns:
            Dictionary mapping user_id to bandwidth limit in Mbps
        """
        self.logger.debug(f"Calculating limits for {len(external_streamers)} users "
                         f"with {available_bandwidth:.2f} Mbps available")
        
        # Ensure minimum available bandwidth
        if available_bandwidth < self.config.min_per_user:
            self.logger.warning(f"Available bandwidth ({available_bandwidth:.2f} Mbps) "
                              f"is less than minimum per user ({self.config.min_per_user} Mbps)")
            return {}
        
        # Calculate limits using selected algorithm
        user_limits = self.algorithm.calculate_limits(
            external_streamers, available_bandwidth, self.config
        )
        
        # Log results
        for user_id, limit in user_limits.items():
            user_data = external_streamers.get(user_id, {})
            user_info = user_data.get('user_data', {})
            username = user_info.get('Name', user_id)
            self.logger.debug(f"Calculated limit for {username}: {limit:.2f} Mbps")
        
        return user_limits
    
    def change_algorithm(self, algorithm_name: str):
        """Change the bandwidth calculation algorithm."""
        self.algorithm = self._create_algorithm(algorithm_name)
        self.config.algorithm = algorithm_name
        self.logger.info(f"Changed bandwidth algorithm to: {algorithm_name}") 