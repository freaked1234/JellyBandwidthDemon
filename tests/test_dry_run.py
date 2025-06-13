import unittest
from unittest.mock import MagicMock
from jellydemon import JellyDemon

class TestDryRunMode(unittest.TestCase):
    def test_no_changes_applied(self):
        daemon = JellyDemon('config.example.yml')
        daemon.config.daemon.dry_run = True
        daemon.config.bandwidth.low_usage_threshold = 0
        session = {
            'Id': 's1',
            'UserId': 'u1',
            'NowPlayingItem': {'Id': 'i1', 'MediaSources': [{'Id': 'ms1'}]},
            'PlayState': {'MediaSourceId': 'ms1', 'PositionTicks': 1}
        }
        external = {'u1': {'session_data': session}}

        daemon.bandwidth_manager.calculate_limits = MagicMock(return_value={'u1': 5.0})
        daemon.jellyfin.set_user_bandwidth_limit = MagicMock()
        daemon.jellyfin.restart_stream = MagicMock()
        daemon.jellyfin.get_user_policy = MagicMock(return_value={'RemoteClientBitrateLimit': 10000000})
        daemon.openwrt.get_total_bandwidth = MagicMock(return_value=100.0)

        with self.assertLogs('jellydemon', level='INFO') as cm:
            daemon.calculate_and_apply_limits(external, current_usage=20.0)

        daemon.jellyfin.set_user_bandwidth_limit.assert_not_called()
        daemon.jellyfin.restart_stream.assert_not_called()
        logs = '\n'.join(cm.output)
        self.assertIn('[DRY RUN] Would change user u1 from 10.00 Mbps to 5.00 Mbps (playing) - would restart stream (session s1)', logs)

    def test_shutdown_logs_restore(self):
        daemon = JellyDemon('config.example.yml')
        daemon.config.daemon.dry_run = True
        daemon.config.daemon.update_interval = 0
        daemon.validate_connectivity = MagicMock(return_value=True)
        daemon.jellyfin.restore_user_bandwidth_limits = MagicMock()

        def cycle():
            daemon.running = False
        daemon.run_single_cycle = cycle

        with self.assertLogs('jellydemon', level='INFO') as cm:
            daemon.run()

        daemon.jellyfin.restore_user_bandwidth_limits.assert_not_called()
        logs = '\n'.join(cm.output)
        self.assertIn('[DRY RUN] Would restore user bandwidth limits to original values', logs)

if __name__ == '__main__':
    unittest.main()
