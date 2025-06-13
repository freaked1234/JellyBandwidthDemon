import unittest
from unittest.mock import MagicMock, patch
from modules.jellyfin_client import JellyfinClient
from modules.config import JellyfinConfig

class TestJellyfinClient(unittest.TestCase):
    def test_restart_stream_endpoints(self):
        cfg = JellyfinConfig(host='localhost', port=8096, api_key='key')
        client = JellyfinClient(cfg)
        session = {
            'Id': 'sess1',
            'UserId': 'user1',
            'NowPlayingItem': {
                'Id': 'item1',
                'MediaSources': [{'Id': 'ms1'}]
            },
            'PlayState': {'PositionTicks': 5}
        }

        with patch.object(client.session, 'post', side_effect=[MagicMock(status_code=204), MagicMock(status_code=204)]) as mock_post, \
             patch('time.sleep'):
            result = client.restart_stream(session)

        self.assertTrue(result)
        base = client.config.base_url
        stop_call = mock_post.call_args_list[0]
        resume_call = mock_post.call_args_list[1]
        self.assertEqual(stop_call.args[0], f"{base}/Sessions/sess1/Playing/Stop")
        resume_url = f"{base}/Sessions/sess1/Playing"
        self.assertEqual(resume_call.args[0], resume_url)
        params = resume_call.kwargs['params']
        expected = {
            'playCommand': 'PlayNow',
            'itemIds': 'item1',
            'startPositionTicks': 5,
            'mediaSourceId': 'ms1',
            'controllingUserId': 'user1'
        }
        self.assertEqual(params, expected)

    def test_get_user_policy_logs_limit(self):
        cfg = JellyfinConfig(host='localhost', port=8096, api_key='key')
        client = JellyfinClient(cfg)
        response = MagicMock(status_code=200)
        response.json.return_value = {'RemoteClientBitrateLimit': 5000000}
        with patch.object(client.session, 'get', return_value=response):
            with self.assertLogs('jellydemon.jellyfin', level='DEBUG') as cm:
                policy = client.get_user_policy('u1')
        self.assertEqual(policy, {'RemoteClientBitrateLimit': 5000000})
        logs = '\n'.join(cm.output)
        self.assertIn('RemoteClientBitrateLimit is 5.00 Mbps', logs)

    def test_set_user_bandwidth_limit_logs_and_restarts(self):
        cfg = JellyfinConfig(host='localhost', port=8096, api_key='key')
        client = JellyfinClient(cfg)
        client.get_user_info = MagicMock(return_value={'Name': 'user1'})
        client.get_user_policy = MagicMock(return_value={'RemoteClientBitrateLimit': 10000000})
        post_resp = MagicMock(status_code=204)
        with patch.object(client.session, 'post', return_value=post_resp):
            client.restart_stream = MagicMock(return_value=True)
            session = {
                'Id': 's1',
                'UserId': 'user1',
                'NowPlayingItem': {'Id': 'i1', 'MediaSources': [{'Id': 'ms1'}]},
                'PlayState': {'MediaSourceId': 'ms1'}
            }
            with self.assertLogs('jellydemon.jellyfin', level='INFO') as cm:
                result = client.set_user_bandwidth_limit('user1', 5.0, session)
        self.assertTrue(result)
        client.restart_stream.assert_called_with(session)
        logs = '\n'.join(cm.output)
        self.assertIn('from 10.00 Mbps to 5.00 Mbps (playing)', logs)
        self.assertIn('restarted stream (session s1)', logs)

if __name__ == '__main__':
    unittest.main()
