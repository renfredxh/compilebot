from __future__ import unicode_literals, print_function
import unittest
import praw
from mock import Mock, patch
import compilebot as cb

"""
Ingetration test cases for creating reddit replies. Tests require reddit login
credentials.

Run the following command from the parent directory in order to run only
this test module: python -m unittest tests.integration.reddit
"""

cb.USER_AGENT = "compilebot ingetration tests run by {}".format(cb.R_USERNAME)
cb.LOG_FILE = "tests.log"

def test_suite():
    cases = [
        TestRedditIntegration
    ]
    alltests = [
        unittest.TestLoader().loadTestsFromTestCase(case) for case in cases
    ]
    return unittest.TestSuite(alltests)

@unittest.skipIf(cb.CONFIG['tests']['integration']['reddit']['skip'],
                 "Test config option set to skip")
class TestRedditIntegration(unittest.TestCase):

    @patch('{}.cb.time.sleep'.format(__name__))
    @patch('{}.cb.praw.objects.Subreddit.get_banned'.format(__name__))
    @patch('{}.cb.compile'.format(__name__))
    def test_compile_request(self, mock_compile, mock_get_banned, mock_sleep):
        test_comment_id = cb.CONFIG['tests']['integration']['reddit']['test_comment']
        accepted_substring = cb.CONFIG['tests']['integration']['reddit']['accepted_substring']
        mock_compile.return_value = {
            'cmpinfo': '',
            'error': 'OK',
            'input': "Hello World",
            'langId': 116,
            'langName': "Python 3",
            'output': "Hello World\n",
            'public': True,
            'result': 15,
            'signal': 0,
            'source': "x = input()\nprint(x)",
            'status': 0,
            'stderr': "",
            'link': 'jnImo8'
        }
        mock_get_banned.return_value = []
        test_r = praw.Reddit(cb.USER_AGENT)
        test_r.login(cb.R_USERNAME, cb.R_PASSWORD)
        test_comment = None
        for message in test_r.get_inbox():
            if message.id == test_comment_id:
                test_comment = message
                break
        if test_comment is None:
            self.skipTest("Test comment not found")

        cb.main()
        test_comment.mark_as_unread()
        self.assertTrue(mock_compile.called)
        user = test_r.get_redditor(cb.R_USERNAME)
        test_reply = user.get_comments(limit=1).next()
        self.assertIn(accepted_substring, test_reply.body)

if __name__ == "__main__":
    unittest.main(exit=False)

