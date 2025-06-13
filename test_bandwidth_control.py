import unittest
from unittest.mock import MagicMock, patch

from modules.jellyfin_client import JellyfinClient
from modules.config import JellyfinConfig


class TestBandwidthControl(unittest.TestCase):
    def setUp(self):
        cfg = JellyfinConfig(host='localhost', port=8096, api_key='key')
        self.client = JellyfinClient(cfg)

    @patch.object(JellyfinClient, 'get_user_info')
    @patch.object(JellyfinClient, 'get_user_policy')
    def test_set_user_bandwidth_limit(self, mock_policy, mock_info):
        mock_policy.return_value = {'RemoteClientBitrateLimit': 0}
        mock_info.return_value = {'Name': 'user'}
        resp = MagicMock(status_code=204)
        with patch.object(self.client.session, 'post', return_value=resp) as mock_post:
            result = self.client.set_user_bandwidth_limit('u1', 25.0)

        self.assertTrue(result)
        expected_policy = {'RemoteClientBitrateLimit': 25_000_000}
        mock_post.assert_called_with(
            f'{self.client.config.base_url}/Users/u1/Policy',
            json=expected_policy
        )

    @patch('time.sleep')
    def test_restart_stream(self, _mock_sleep):
        session = {
            'Id': 's1',
            'UserId': 'u1',
            'NowPlayingItem': {'Id': 'i1', 'MediaSources': [{'Id': 'ms1'}]},
            'PlayState': {'PositionTicks': 5}
        }
        resp = MagicMock(status_code=204)
        with patch.object(self.client.session, 'post', return_value=resp) as mock_post:
            result = self.client.restart_stream(session)

        self.assertTrue(result)
        base = self.client.config.base_url
        stop_call = mock_post.call_args_list[0]
        resume_call = mock_post.call_args_list[1]
        self.assertEqual(stop_call.args[0], f"{base}/Sessions/s1/Playing/Stop")
        self.assertEqual(resume_call.args[0], f"{base}/Sessions/s1/Playing")

if __name__ == '__main__':
    unittest.main()
