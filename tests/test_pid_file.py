import os
import tempfile
import unittest
from unittest.mock import MagicMock

from jellydemon import JellyDemon

class TestPidFile(unittest.TestCase):
    def setUp(self):
        self.pid_file = os.path.join(tempfile.gettempdir(), "jd_test.pid")
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        self.daemon = JellyDemon('config.example.yml')
        self.daemon.validate_connectivity = MagicMock(return_value=True)
        self.daemon.config.daemon.update_interval = 0
        self.daemon.config.daemon.pid_file = self.pid_file

    def tearDown(self):
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    def test_pid_file_created_and_removed(self):
        flag = {}
        def cycle():
            flag['exists'] = os.path.exists(self.pid_file)
            self.daemon.running = False
        self.daemon.run_single_cycle = cycle

        result = self.daemon.run()

        self.assertEqual(result, 0)
        self.assertTrue(flag.get('exists'))
        self.assertFalse(os.path.exists(self.pid_file))

    def test_prevent_multiple_instances(self):
        with open(self.pid_file, 'w') as f:
            f.write('123')
        self.daemon.run_single_cycle = MagicMock()

        result = self.daemon.run()

        self.assertEqual(result, 1)
        self.daemon.run_single_cycle.assert_not_called()
        self.assertTrue(os.path.exists(self.pid_file))

if __name__ == '__main__':
    unittest.main()
