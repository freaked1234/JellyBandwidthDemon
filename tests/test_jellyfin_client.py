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

if __name__ == '__main__':
    unittest.main()
