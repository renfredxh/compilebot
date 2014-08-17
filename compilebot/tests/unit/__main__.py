"""Execute all unit tests in the current directory.

Run: python -m tests.unit
(Note: Must be run from the compilebot directory)

"""

from . import *
import unittest

def main():
    print("Running CompileBot unit tests")
    test_suites = [
        reply.test_suite(),
        praw.test_suite(),
    ]
    all_tests = unittest.TestSuite(test_suites)
    unittest.TextTestRunner().run(all_tests)

if __name__ == "__main__":
    main()
