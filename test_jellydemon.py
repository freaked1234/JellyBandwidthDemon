import unittest
from unittest.mock import MagicMock

from jellydemon import JellyDemon


class TestJellyDemonMocked(unittest.TestCase):
    def setUp(self):
        self.daemon = JellyDemon('config.example.yml')
        # Replace real clients with mocks
        self.daemon.openwrt = MagicMock()
        self.daemon.jellyfin = MagicMock()
        self.daemon.network_utils = MagicMock()
        self.daemon.bandwidth_manager = MagicMock()

    def test_validate_connectivity(self):
        self.daemon.openwrt.test_connection.return_value = True
        self.daemon.jellyfin.test_connection.return_value = True
        self.assertTrue(self.daemon.validate_connectivity())

    def test_run_single_cycle_calls_apply(self):
        self.daemon.get_current_bandwidth_usage = MagicMock(return_value=10.0)
        external = {'u1': {'session_data': {}}}
        self.daemon.get_external_streamers = MagicMock(return_value=external)
        self.daemon.calculate_and_apply_limits = MagicMock()

        self.daemon.run_single_cycle()

        self.daemon.calculate_and_apply_limits.assert_called_with(external, 10.0)


if __name__ == '__main__':
    unittest.main()
