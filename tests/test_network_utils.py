import unittest
from modules.network_utils import NetworkUtils
from modules.config import NetworkConfig

class TestNetworkUtils(unittest.TestCase):
    def test_is_external_ip_normal_mode(self):
        config = NetworkConfig(internal_ranges=['192.168.0.0/16', '10.0.0.0/8'])
        utils = NetworkUtils(config)
        self.assertFalse(utils.is_external_ip('192.168.1.1'))
        self.assertFalse(utils.is_external_ip('10.20.30.40'))
        self.assertTrue(utils.is_external_ip('172.16.0.1'))
        self.assertTrue(utils.is_external_ip('8.8.8.8'))

    def test_is_external_ip_test_mode(self):
        config = NetworkConfig(
            internal_ranges=['192.168.0.0/16'],
            test_mode=True,
            test_external_ranges=['203.0.113.0/24']
        )
        utils = NetworkUtils(config)
        self.assertTrue(utils.is_external_ip('203.0.113.5'))
        self.assertFalse(utils.is_external_ip('192.168.1.10'))
        # In test mode IPs not in test_external_ranges are treated as internal
        self.assertFalse(utils.is_external_ip('8.8.8.8'))

if __name__ == '__main__':
    unittest.main()
