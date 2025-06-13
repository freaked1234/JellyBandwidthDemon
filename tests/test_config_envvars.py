import os
import tempfile
import unittest
from modules.config import Config

class TestConfigEnvVars(unittest.TestCase):
    def test_env_var_substitution(self):
        yaml_content = """
router:
  host: 192.168.1.1
  username: root
  password: ${TEST_ROUTER_PASS}
jellyfin:
  host: localhost
  port: 8096
  api_key: ${TEST_JELLY_API}
network:
  internal_ranges:
    - "192.168.0.0/16"
"""
        with tempfile.NamedTemporaryFile('w+', delete=False) as tmp:
            tmp.write(yaml_content)
            tmp_path = tmp.name

        os.environ['TEST_ROUTER_PASS'] = 'secret'
        os.environ['TEST_JELLY_API'] = 'key'

        cfg = Config(tmp_path)
        self.assertEqual(cfg.router.password, 'secret')
        self.assertEqual(cfg.jellyfin.api_key, 'key')

        os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
