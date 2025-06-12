#!/usr/bin/env python3
"""
JellyDemon Testing Script - Session and Bandwidth Control
Test script for checking active sessions, setting bandwidth, and forcing a session restart.
"""

import os
import sys
import json
import requests
import time # Import the time module for the delay
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlencode


# =============================================================================
# TEST CONFIGURATION - Modify these values for testing
# =============================================================================
TARGET_IP = "178.165.192.135"  # IP address to target for bandwidth change
TARGET_BANDWIDTH = 20.00       # Bandwidth limit to apply (in Mbps)

# =============================================================================
# Setup and Configuration
# =============================================================================

# Load environment variables
load_dotenv()

# Jellyfin configuration
JELLYFIN_HOST = "192.168.1.243"
JELLYFIN_PORT = 8096
JELLYFIN_API_KEY = os.getenv("JELLY_API")
JELLYFIN_BASE_URL = f"http://{JELLYFIN_HOST}:{JELLYFIN_PORT}"

if not JELLYFIN_API_KEY:
    print("ERROR: JELLY_API environment variable not set!")
    print("Please add JELLY_API=your_api_key to your .env file")
    sys.exit(1)

# This is the modern, recommended way to authenticate with an API Key.
BASE_HEADERS = {
    "Authorization": f'MediaBrowser Token="{JELLYFIN_API_KEY}"',
    "Accept": "application/json",
}

def make_jellyfin_request(endpoint, method="GET", data=None):
    """Make a request to the Jellyfin API"""
    url = f"{JELLYFIN_BASE_URL}{endpoint}"
    headers = BASE_HEADERS.copy()
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        
        if response.status_code == 204: # Handles successful POST with No Content
            return {}
        return response.json() if response.content else {}
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request to {url} failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"--> Response Status: {e.response.status_code}")
            print(f"--> Response Body: {e.response.text}")
        return None

def get_active_sessions():
    """Get all active Jellyfin sessions"""
    sessions = make_jellyfin_request("/Sessions")
    if sessions is None:
        return []
    
    active_sessions = [s for s in sessions if s.get("NowPlayingItem")]
    print(f"Found {len(active_sessions)} active streaming sessions.")
    return active_sessions

def get_user_policy(user_id):
    """Get user policy by fetching the full user object."""
    user_data = make_jellyfin_request(f"/Users/{user_id}")
    if user_data and "Policy" in user_data:
        return user_data["Policy"]
    else:
        print(f"Could not find 'Policy' object in user data for {user_id}")
        return None

def set_user_bandwidth_limit(user_id, bandwidth_mbps):
    """Set bandwidth limit for a user by POSTing to the /Policy endpoint."""
    bandwidth_bps = int(bandwidth_mbps * 1_000_000)
    
    current_policy = get_user_policy(user_id)
    if not current_policy:
        print(f"ERROR: Could not get current policy for user {user_id}")
        return False
    
    current_policy["RemoteClientBitrateLimit"] = bandwidth_bps
    
    print(f"Setting bandwidth for {user_id} to {bandwidth_bps} bps...")
    result = make_jellyfin_request(f"/Users/{user_id}/Policy", method="POST", data=current_policy)
    
    return result is not None


def force_stream_restart(session_id, item_id, position_ticks, media_source_id, user_id):
    # 1. STOP
    make_jellyfin_request(f"/Sessions/{session_id}/Playing/Stop", method="POST", data={})
    time.sleep(0.8)

    params = {
        "playCommand": "PlayNow",
        "itemIds": item_id,
        "startPositionTicks": position_ticks,
        "mediaSourceId": media_source_id,
        "controllingUserId": user_id
    }
    qs = urlencode(params)
    resume_endpoint = f"/Sessions/{session_id}/Playing?{qs}"

    # empty body – Jellyfin only needs the query string
    return make_jellyfin_request(resume_endpoint, method="POST", data={}) is not None


def format_bandwidth(bps):
    """Format bandwidth from bits per second to human readable"""
    if bps is None or bps == 0:
        return "No limit"
    
    mbps = bps / 1_000_000
    return f"{mbps:.1f} Mbps"

def display_session_info(sessions):
    """Display information about active sessions"""
    print("\n" + "="*80)
    print("ACTIVE JELLYFIN SESSIONS")
    print("="*80)

    if not sessions:
        print("No active playing sessions found.")
        return {}
    
    session_users = {}
    
    for i, session in enumerate(sessions, 1):
        user_name = session.get("UserName", "Unknown User")
        user_id = session.get("UserId", "")
        client_ip = session.get("RemoteEndPoint", "Unknown IP")
        session_id = session.get("Id", "")

        # Extract all info needed for the resume command
        play_state = session.get("PlayState", {})
        now_playing = session.get("NowPlayingItem", {})
        
        item_id = now_playing.get("Id", "")
        position_ticks = play_state.get("PositionTicks", 0)
        media_source_id = (play_state.get("MediaSourceId") or
                   now_playing.get("MediaSources", [{}])[0].get("Id", ""))


        if not all([user_id, session_id, item_id, media_source_id]):
            print(f"  - WARNING: Incomplete session data for user {user_name}. Skipping.")
            continue

        user_policy = get_user_policy(user_id)
        current_limit = "Unknown"
        if user_policy:
            limit_bps = user_policy.get("RemoteClientBitrateLimit", 0)
            current_limit = format_bandwidth(limit_bps)
        
        session_users[client_ip] = {
            "user_id": user_id, 
            "user_name": user_name,
            "session_id": session_id,
            "item_id": item_id,
            "position_ticks": position_ticks,
            "media_source_id": media_source_id
        }
        
        print(f"  - User: {user_name:<15} IP: {client_ip:<15} Limit: {current_limit}")
    
    print("="*80)
    return session_users

def main():
    """Main testing function"""
    global TARGET_IP

    print("JellyDemon Bandwidth Control Test")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Jellyfin Server: {JELLYFIN_BASE_URL}")
    print()
    
    print("Testing Jellyfin API connectivity...")
    system_info = make_jellyfin_request("/System/Info")
    if not system_info:
        print("ERROR: Could not connect to Jellyfin API! Check HOST, PORT, and API Key.")
        sys.exit(1)
    
    print(f"✓ Connected to Jellyfin: {system_info.get('ProductName', 'Unknown')} v{system_info.get('Version', 'Unknown')}")
    
    print("\nFetching initial sessions...")
    sessions = get_active_sessions()
    session_users = display_session_info(sessions)
    
    if not session_users:
        print("\nNo active sessions to work with. Exiting.")
        return
    
    print(f"\nTarget Configuration:")
    print(f"  - Target IP: {TARGET_IP}")
    print(f"  - Target Bandwidth: {TARGET_BANDWIDTH} Mbps\n")
    
    if TARGET_IP not in session_users:
        print(f"WARNING: Target IP {TARGET_IP} not found in active sessions.")
        if session_users:
            first_ip = list(session_users.keys())[0]
            choice = input(f"Would you like to test with '{first_ip}' instead? (y/n): ").strip().lower()
            if choice == 'y':
                TARGET_IP = first_ip
                print(f"--> Using '{TARGET_IP}' for this test.")
            else:
                print("Exiting without making changes.")
                return
        else:
            return
    
    target_user = session_users[TARGET_IP]
    print(f"\nFound target session: User '{target_user['user_name']}' from IP '{TARGET_IP}'")
    
    print("\n1. Applying new bandwidth limit...")
    success = set_user_bandwidth_limit(target_user['user_id'], TARGET_BANDWIDTH)
    
    if success:
        print("✓ Bandwidth limit POST request sent successfully.")
        
        print("\n2. Verifying new bandwidth limit...")
        updated_policy = get_user_policy(user_id=target_user['user_id'])
        if updated_policy:
            new_limit_bps = updated_policy.get("RemoteClientBitrateLimit", 0)
            new_limit_str = format_bandwidth(new_limit_bps)
            print(f"   Verified new limit from server: {new_limit_str}")
            
            if new_limit_bps == int(TARGET_BANDWIDTH * 1_000_000):
                print("✓ SUCCESS: Bandwidth limit change was verified.")

                print("\n3. Forcing client to restart stream.")
                restart_choice = input(f"   Ready to force restart for '{target_user['user_name']}'? (y/n): ").strip().lower()
                if restart_choice == 'y':
                    restart_success = force_stream_restart(
                        session_id=target_user['session_id'],
                        item_id=target_user['item_id'],
                        position_ticks=target_user['position_ticks'],
                        media_source_id=target_user['media_source_id'],
                        user_id=target_user['user_id']
                    )
                    if restart_success:
                        print("   ✓ Stream restart command sent successfully.")
                        print("   --> Observe the client. It should buffer and reconnect with the new quality.")
                    else:
                        print("   ✗ FAILED: The request to restart the stream failed.")
                else:
                    print("   Skipping stream restart.")

            else:
                print("⚠ WARNING: Applied limit doesn't match expected value on server.")
        else:
            print("ERROR: Could not verify new bandwidth limit.")
    else:
        print("✗ FAILED: The request to apply the bandwidth limit failed.")

if __name__ == "__main__":
    main()

