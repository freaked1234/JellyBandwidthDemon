import unittest
from unittest.mock import MagicMock

from jellydemon import JellyDemon


class TestExternalUserTracking(unittest.TestCase):
    def test_user_start_stop_and_threshold_logging(self):
        daemon = JellyDemon('config.example.yml')
        daemon.config.bandwidth.low_usage_threshold = 10
        daemon.calculate_and_apply_limits = MagicMock()

        daemon.get_current_bandwidth_usage = MagicMock(return_value=5.0)
        daemon.get_external_streamers = MagicMock(return_value={'u1': {'ip': '2.2.2.2'}})
        with self.assertLogs('jellydemon', level='INFO') as cm:
            daemon.run_single_cycle()
        logs = '\n'.join(cm.output)
        self.assertIn('User u1 started streaming from 2.2.2.2', logs)
        self.assertNotIn('high-demand', logs)

        daemon.get_current_bandwidth_usage = MagicMock(return_value=15.0)
        daemon.get_external_streamers = MagicMock(return_value={})
        with self.assertLogs('jellydemon', level='INFO') as cm2:
            daemon.run_single_cycle()
        logs2 = '\n'.join(cm2.output)
        self.assertIn('User u1 stopped streaming', logs2)
        self.assertIn('entering high-demand mode', logs2)


if __name__ == '__main__':
    unittest.main()
