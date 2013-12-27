from __future__ import unicode_literals, print_function
import unittest
import compilebot as cb

class TestReplyFunctions(unittest.TestCase):

    def setUp(self):
        self.user = cb.R_USERNAME

    def test_parser(self):
        # Test source code surrounded by additional comments.
        body = ("This sentence should not be included. +/u/{user} python 3\n\n"
                "    print(\"Test\")\n\n"
                "This sentence should not be included.".format(user=self.user))
        args, source, stdin = cb.parse_comment(body)
        self.assertEqual(args, 'python 3')
        self.assertEqual(source, 'print(\"Test\")')
        self.assertEqual(stdin, '')
        # Test multi-line source, input, and additional arguments.
        body = ("+/u/{user} python 3 --time\n\n"
                "    \n        x = input()\n    print(\"x\")\n    \n\n\n"
                "Input: \n\n    5\n    6\n    7").format(user=self.user)
        args, source, stdin = cb.parse_comment(body)
        self.assertEqual(args, 'python 3 --time')
        self.assertEqual(source, '    x = input()\nprint(\"x\")\n')
        self.assertEqual(stdin, '5\n6\n7')
        # Should raise an attribute error when there an indented code
        # block is missing.
        body = "+/u/{user} Java\n\n Not source code\n\n"
        self.assertRaises(AttributeError, cb.parse_comment, (body))

if __name__ == '__main__':
    unittest.main()