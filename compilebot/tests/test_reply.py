from __future__ import unicode_literals, print_function
import unittest
import random
import string 
from imp import reload
import compilebot as cb

"""
Unit test cases for functions that format, create, and edit replies.

Run from parent directory: python -m unittest tests.test_reply
"""

cb.USER_AGENT = "compilebot unit tests run by {}".format(cb.R_USERNAME)

def log(text, *args, **kwargs):
    print(text)

def reddit_id(length=6):
    "Emulate a reddit id with a random string of letters and digits"
    return ''.join(random.choice(string.ascii_lowercase + 
                   string.digits) for x in range(length))
    
class TestParseComment(unittest.TestCase):

    def setUp(self):
        self.user = cb.R_USERNAME

    def test_parser(self):
        body = ("This sentence should not be included. +/u/{user} python 3\n\n"
                "    print(\"Test\")\n\n"
                "This sentence should not be included.".format(user=self.user))
        args, source, stdin = cb.parse_comment(body)
        self.assertEqual(args, 'python 3')
        self.assertEqual(source, 'print(\"Test\")')
        self.assertEqual(stdin, '')
    
    def test_parse_args(self):
        body = ("+/u/{user} python 3 --time\n\n"
                "    \n        x = input()\n    print(\"x\")\n    \n\n\n"
                "Input: \n\n    5\n    6\n    7").format(user=self.user)
        args, source, stdin = cb.parse_comment(body)
        self.assertEqual(args, 'python 3 --time')
        self.assertEqual(source, '    x = input()\nprint(\"x\")\n')
        self.assertEqual(stdin, '5\n6\n7')
        
    def test_errors(self):
        # Should raise an attribute error when there an indented code
        # block is missing.
        body = "+/u/{user} Java\n\n Source code missing\n\n"
        self.assertRaises(AttributeError, cb.parse_comment, (body))

class TestCreateReply(unittest.TestCase):

    class Comment(object):
        """Simplified version of a PRAW comment object for testing"""
        def __init__(self, body):
            self.body = body
            self.id = reddit_id()
            self.permalink = ''
    
    def setUp(self):
        self.user = cb.R_USERNAME
    
    def test_create_reply(self):
        def compile(*args, **kwargs):
            return {
                'cmpinfo': "",
                'input': "",
                'langName': "Python",
                'output': "Test",
                'result': 15,
                'stderr': "",
                'link': ''
            }
        cb.compile = compile
        body = ("+/u/{user} python\n\n"
                "    print(\"Test\")\n\n".format(user=self.user))
        comment = self.Comment(body)
        reply = cb.create_reply(comment)
        self.assertIn("Output:\n\n\n    Test\n", reply.text)
        
    def test_bad_format(self):
        body = "+/u/{user} Formatted incorrectly".format(user=self.user)
        comment = self.Comment(body)
        reply = cb.create_reply(comment)
        self.assertIsInstance(reply, cb.MessageReply)
        
    def test_missing_language(self):
        def compile(*args, **kwargs):
            raise cb.ideone.LanguageNotFoundError(error_msg, similar_langs)
        cb.compile = compile
        error_msg = "Language Error Message"
        similar_langs = ["FooBar", "BazzScript", "Z 1-X"]
        # When the compile function returns an LanguageNotFoundError,
        # compilebot should notify the user the possible languages they 
        # were looking for via message reply.
        body = "+/u/{user} Foo\n\n    print(\"Test\")\n\n".format(user=self.user)
        comment = self.Comment(body)
        reply = cb.create_reply(comment)
        self.assertIsInstance(reply, cb.MessageReply)
        self.assertTrue(all(lang in reply.text for lang in similar_langs))
        
    def tearDown(self):
        reload(cb)
    
if __name__ == '__main__':
    unittest.main()