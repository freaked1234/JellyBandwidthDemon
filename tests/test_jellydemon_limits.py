import unittest
from unittest.mock import MagicMock, patch
from jellydemon import JellyDemon

class TestJellyDemonLimits(unittest.TestCase):
    def test_restart_called_when_limit_changes(self):
        daemon = JellyDemon('config.example.yml')
        daemon.config.bandwidth.low_usage_threshold = 0
        session = {
            'Id': 's1',
            'UserId': 'u1',
            'NowPlayingItem': {'Id': 'i1', 'MediaSources': [{'Id': 'ms1'}]},
            'PlayState': {'MediaSourceId': 'ms1', 'PositionTicks': 1}
        }
        external = {'u1': {'session_data': session}}

        daemon.bandwidth_manager.calculate_limits = MagicMock(return_value={'u1': 5.0})
        daemon.jellyfin.set_user_bandwidth_limit = MagicMock(return_value=True)
        daemon.jellyfin.restart_stream = MagicMock(return_value=True)
        daemon.openwrt.get_total_bandwidth = MagicMock(return_value=100.0)

        daemon.calculate_and_apply_limits(external, current_usage=20.0)

        daemon.jellyfin.set_user_bandwidth_limit.assert_called_with('u1', 5.0)
        daemon.jellyfin.restart_stream.assert_called_with(session)

if __name__ == '__main__':
    unittest.main()
