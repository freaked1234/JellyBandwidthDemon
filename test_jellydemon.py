#!/usr/bin/env python3
"""
Test script for JellyDemon components
"""

import sys
import argparse
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.config import Config
from modules.logger import setup_logging
from modules.openwrt_client import OpenWRTClient
from modules.jellyfin_client import JellyfinClient
from modules.bandwidth_manager import BandwidthManager
from modules.network_utils import NetworkUtils


def test_config(config_path: str):
    """Test configuration loading and validation."""
    print("Testing configuration...")
    try:
        config = Config(config_path)
        print("✓ Configuration loaded successfully")
        
        print(f"  Router: {config.router.host}:{config.router.luci_port}")
        print(f"  Jellyfin: {config.jellyfin.base_url}")
        print(f"  Algorithm: {config.bandwidth.algorithm}")
        print(f"  Internal ranges: {config.network.internal_ranges}")
        
        return config
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return None


def test_network_utils(config):
    """Test network utilities and IP checking."""
    print("\nTesting network utilities...")
    try:
        net_utils = NetworkUtils(config.network)
        
        # Test some IPs
        test_ips = [
            "192.168.1.100",  # Internal
            "8.8.8.8",        # External
            "10.0.0.1",       # Internal
            "1.1.1.1"         # External
        ]
        
        for ip in test_ips:
            is_external = net_utils.is_external_ip(ip)
            status = "external" if is_external else "internal"
            print(f"  {ip}: {status}")
        
        print("✓ Network utilities working")
        return net_utils
    except Exception as e:
        print(f"✗ Network utilities error: {e}")
        return None


def test_openwrt_connection(config):
    """Test OpenWRT router connection."""
    print("\nTesting OpenWRT connection...")
    try:
        client = OpenWRTClient(config.router)
        
        if client.test_connection():
            print("✓ OpenWRT connection successful")
            
            # Try to get bandwidth info
            try:
                usage = client.get_bandwidth_usage()
                total = client.get_total_bandwidth()
                print(f"  Current usage: {usage:.2f} Mbps")
                print(f"  Total capacity: {total:.2f} Mbps")
            except Exception as e:
                print(f"  ⚠ Could not get bandwidth info: {e}")
            
            return client
        else:
            print("✗ OpenWRT connection failed")
            return None
            
    except Exception as e:
        print(f"✗ OpenWRT connection error: {e}")
        return None


def test_jellyfin_connection(config):
    """Test Jellyfin server connection."""
    print("\nTesting Jellyfin connection...")
    try:
        client = JellyfinClient(config.jellyfin)
        
        if client.test_connection():
            print("✓ Jellyfin connection successful")
            
            # Try to get session info
            try:
                sessions = client.get_active_sessions()
                print(f"  Active sessions: {len(sessions)}")
                
                users = client.get_all_users()
                print(f"  Total users: {len(users)}")
                
            except Exception as e:
                print(f"  ⚠ Could not get session info: {e}")
            
            return client
        else:
            print("✗ Jellyfin connection failed")
            return None
            
    except Exception as e:
        print(f"✗ Jellyfin connection error: {e}")
        return None


def test_bandwidth_algorithms(config):
    """Test bandwidth calculation algorithms."""
    print("\nTesting bandwidth algorithms...")
    try:
        manager = BandwidthManager(config.bandwidth)
        
        # Mock external streamers data
        mock_streamers = {
            "user1": {
                "ip": "1.2.3.4",
                "user_data": {"Name": "TestUser1", "Policy": {"IsAdministrator": False}},
                "session_data": {"NowPlayingItem": {"Bitrate": 5000000}}
            },
            "user2": {
                "ip": "5.6.7.8", 
                "user_data": {"Name": "TestUser2", "Policy": {"IsAdministrator": True}},
                "session_data": {"NowPlayingItem": {"Bitrate": 10000000}}
            }
        }
        
        available_bandwidth = 50.0  # 50 Mbps
        
        # Test each algorithm
        algorithms = ["equal_split", "priority_based", "demand_based"]
        for algorithm in algorithms:
            manager.change_algorithm(algorithm)
            limits = manager.calculate_limits(mock_streamers, available_bandwidth)
            print(f"  {algorithm}:")
            for user_id, limit in limits.items():
                user_name = mock_streamers[user_id]["user_data"]["Name"]
                print(f"    {user_name}: {limit:.2f} Mbps")
        
        print("✓ Bandwidth algorithms working")
        return manager
        
    except Exception as e:
        print(f"✗ Bandwidth algorithm error: {e}")
        return None


def test_full_integration(config):
    """Test full integration with all components."""
    print("\nTesting full integration...")
    try:
        # Initialize all components
        openwrt = OpenWRTClient(config.router)
        jellyfin = JellyfinClient(config.jellyfin)
        bandwidth_manager = BandwidthManager(config.bandwidth)
        network_utils = NetworkUtils(config.network)
        
        # Test connectivity
        openwrt_ok = openwrt.test_connection()
        jellyfin_ok = jellyfin.test_connection()
        
        if not (openwrt_ok and jellyfin_ok):
            print("✗ Not all services are accessible")
            return False
        
        # Get real data
        current_usage = openwrt.get_bandwidth_usage()
        total_bandwidth = openwrt.get_total_bandwidth()
        sessions = jellyfin.get_active_sessions()
        
        print(f"  Current bandwidth usage: {current_usage:.2f} Mbps")
        print(f"  Total bandwidth: {total_bandwidth:.2f} Mbps")
        print(f"  Active sessions: {len(sessions)}")
        
        # Find external streamers
        external_streamers = {}
        for session in sessions:
            user_id = session.get('UserId')
            remote_endpoint = session.get('RemoteEndPoint', '')
            
            if user_id and remote_endpoint:
                client_ip = remote_endpoint.split(':')[0]
                if network_utils.is_external_ip(client_ip):
                    user_info = jellyfin.get_user_info(user_id)
                    external_streamers[user_id] = {
                        'ip': client_ip,
                        'session_data': session,
                        'user_data': user_info
                    }
        
        print(f"  External streamers: {len(external_streamers)}")
        
        if external_streamers:
            # Calculate bandwidth limits
            available = total_bandwidth - current_usage - config.bandwidth.reserved_bandwidth
            limits = bandwidth_manager.calculate_limits(external_streamers, available)
            
            print("  Calculated limits:")
            for user_id, limit in limits.items():
                user_info = external_streamers[user_id]['user_data']
                username = user_info.get('Name', user_id) if user_info else user_id
                print(f"    {username}: {limit:.2f} Mbps")
        
        print("✓ Full integration test successful")
        return True
        
    except Exception as e:
        print(f"✗ Integration test error: {e}")
        return False


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="JellyDemon Test Suite")
    parser.add_argument("--config", "-c", default="config.yml", help="Configuration file")
    parser.add_argument("--test", choices=[
        "config", "network", "openwrt", "jellyfin", "bandwidth", "integration", "all"
    ], default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    print("JellyDemon Test Suite")
    print("=" * 50)
    
    # Load config first
    config = test_config(args.config)
    if not config:
        print("Cannot proceed without valid configuration")
        sys.exit(1)
    
    # Setup logging
    logger = setup_logging(config)
    
    tests = {
        "config": lambda: test_config(args.config),
        "network": lambda: test_network_utils(config),
        "openwrt": lambda: test_openwrt_connection(config),
        "jellyfin": lambda: test_jellyfin_connection(config),
        "bandwidth": lambda: test_bandwidth_algorithms(config),
        "integration": lambda: test_full_integration(config)
    }
    
    if args.test == "all":
        # Run all tests
        success = True
        for test_name, test_func in tests.items():
            if test_name == "config":
                continue  # Already tested
            result = test_func()
            if not result:
                success = False
        
        print("\n" + "=" * 50)
        if success:
            print("✓ All tests passed!")
        else:
            print("⚠ Some tests failed - check the output above")
            
    else:
        # Run specific test
        if args.test in tests:
            tests[args.test]()
        else:
            print(f"Unknown test: {args.test}")


if __name__ == "__main__":
    main() 