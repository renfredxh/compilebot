# This script runs all of the suites from each unit test file.
# Run this file from the parent directory with the following command:
# python -m tests.run_all
from tests import *
import unittest

def main():
    test_suites = [
        test_reply.test_suite(),
        test_compiler.test_suite()
    ]
    all_tests = unittest.TestSuite(test_suites)
    unittest.TextTestRunner().run(all_tests)

if __name__ == "__main__":
    main()
