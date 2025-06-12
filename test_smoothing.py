import unittest
from unittest.mock import patch

from jellydemon import JellyDemon

class BandwidthSmoothingTest(unittest.TestCase):
    def test_rolling_average(self):
        daemon = JellyDemon('config.example.yml')
        daemon.config.bandwidth.spike_duration = 3

        values = [10, 100, 10, 10]
        times = [0, 10, 20, 200]

        with patch.object(daemon.openwrt, 'get_bandwidth_usage', side_effect=values):
            with patch('jellydemon.time.time', side_effect=times):
                results = [daemon.get_current_bandwidth_usage() for _ in values]

        self.assertAlmostEqual(results[0], 10.0, places=2)
        self.assertAlmostEqual(results[1], 55.0, places=2)
        self.assertAlmostEqual(results[2], 40.0, places=2)
        self.assertAlmostEqual(results[3], 10.0, places=2)

if __name__ == '__main__':
    unittest.main()
