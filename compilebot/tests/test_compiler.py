from __future__ import unicode_literals, print_function
import unittest
import compilebot as cb

"""
Unit test cases for the compile function. Tests require an ideone login
credentials.

Run the following command from the parent directory in order to run only
this test module: python -m unittest tests.test_compiler
"""

cb.USER_AGENT = "compilebot unit tests run by {}".format(cb.R_USERNAME)
cb.LOG_FILE = "tests.log"

def test_suite():
    cases = [
        TestCompile
    ]
    alltests = [
        unittest.TestLoader().loadTestsFromTestCase(case) for case in cases
    ]
    return unittest.TestSuite(alltests)
    
    
class TestCompile(unittest.TestCase):


    def test_compile(self):
        expected_details = {
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
        }
        source = "x = input()\nprint(x)"
        lang = "python 3"
        stdin = "Hello World"
        details = cb.compile(source, lang, stdin)
        self.assertTrue(details['link'])
        self.assertDictContainsSubset(expected_details, details)

     
if __name__ == "__main__":
    unittest.main(exit=False)
