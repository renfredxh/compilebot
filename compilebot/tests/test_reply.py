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
    """Emulate a reddit id with a random string of letters and digits"""
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
    
    # Simplified version of a PRAW comment for testing purposes
    class Comment(object):
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
                'link': ""
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
        
class TestDetectSpam(unittest.TestCase):
    
    class Comment(object):
        def __init__(self):
            self.author = ''
            self.permalink = ''
    
    def create_reply(self, spam):
        details = {
            'output': spam,
            'source': '',
            'stderr': ''
        }
        text = "Output:\n\n\n{}\n".format(spam)
        reply = cb.CompiledReply(text, details)
        reply.parent_comment = self.Comment()
        return reply
        
    def test_line_breaks(self):
        spam = "    \n" * (cb.LINE_LIMIT + 1)
        reply = self.create_reply(spam)
        self.assertIn("Excessive line breaks", reply.detect_spam())
        
    def test_char_limit(self):
        spam = "a" * (cb.CHAR_LIMIT + 1)
        reply = self.create_reply(spam)
        self.assertIn("Excessive character count", reply.detect_spam())
    
    @unittest.skipIf(len(cb.SPAM_PHRASES) < 1, "No spam phrases set")    
    def test_spam_phrases(self):
        spam = cb.SPAM_PHRASES[0]
        reply = self.create_reply(spam)
        self.assertIn("Spam phrase detected", reply.detect_spam())
        
    def test_permission_denied(self):
        spam = ""
        reply = self.create_reply(spam)
        reply.compile_details['stderr'] = "'rm -rf /*': Permission denied"
        self.assertIn("Illegal system call detected", reply.detect_spam())
        
if __name__ == '__main__':
    unittest.main()