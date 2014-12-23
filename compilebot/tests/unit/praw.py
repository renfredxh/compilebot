from __future__ import unicode_literals, print_function
import unittest
import compilebot as cb
from sys import modules
from mock import Mock, patch
from tests import helpers

"""
Unit test cases for functions, methods, and classes that directly integrate
with the praw API. All tests in this module shouldn't make any requests
to reddit or ideone.

Run the following command from the compilebot directory in order to run only
this test module: python -m unittest tests.unit.praw
"""

cb.LOG_FILE = helpers.LOG_FILE

def test_suite():
    cases = [
        TestSendModMail, TestGetBanned, TestSendAdminMessage, TestMain
    ]
    alltests = [
        unittest.TestLoader().loadTestsFromTestCase(case) for case in cases
    ]
    return unittest.TestSuite(alltests)


class TestSendModMail(unittest.TestCase):

    @patch('{}.cb.praw.Reddit'.format(__name__), autospec=True)
    def test_send_modmail(self, mock_reddit):
        subreddit, subject, body = 'MySub', 'Test Subject', 'Hello'
        r = mock_reddit.return_value
        cb.SUBREDDIT = subreddit
        mock_subreddit = Mock(name='MySub Mock')
        r.get_subreddit.return_value = mock_subreddit

        cb.send_modmail(subject, body, r)
        r.get_subreddit.assert_called_with(subreddit)
        r.send_message.assert_called_once_with(mock_subreddit, subject, body)

class TestGetBanned(unittest.TestCase):

    @patch('{}.cb.praw.Reddit'.format(__name__), autospec=True)
    def test_get_banned(self, mock_reddit):
        r = mock_reddit.return_value
        subreddit = 'MySub'
        cb.SUBREDDIT = subreddit
        mock_user = Mock()
        mock_user.name = 'TrOl1UseR'
        mock_subreddit = Mock(name='MySub Mock')
        mock_subreddit.get_banned.return_value = [mock_user]
        r.get_subreddit.return_value = mock_subreddit

        self.assertEqual(cb.get_banned(r), set(['trol1user']))
        r.get_subreddit.assert_called_with(subreddit)

class TestSendAdminMessage(unittest.TestCase):

    @patch('{}.cb.praw.Reddit'.format(__name__), autospec=True)
    def test_send_admin_message(self, mock_reddit):
        r = mock_reddit.return_value
        cb.ADMIN = 'AdminUser'
        body = "Hello Admin"
        cb.log(body, alert=True)
        args, kwargs = r.send_message.call_args
        self.assertTrue(body in args[2])
        r.send_message.assert_called_once_with('AdminUser', args[1], args[2])

class TestMain(unittest.TestCase):

    @patch('{}.cb.process_unread'.format(__name__), autospec=True)
    @patch('{}.cb.praw.Reddit'.format(__name__), autospec=True)
    def test_main(self, mock_reddit, mock_process_unread):
        r = mock_reddit.return_value
        mock_inbox = [Mock(), Mock(), Mock()]
        r.get_unread.return_value = mock_inbox
        cb.main()
        r.login.assert_called_with(cb.R_USERNAME, cb.R_PASSWORD)
        for new in mock_inbox:
            mock_process_unread.assert_any_call(new, r)
            new.mark_as_read.assert_called_with()

if __name__ == "__main__":
    unittest.main(exit=False)

