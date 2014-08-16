import string
import random
from mock import Mock

LOG_FILE = "tests.log"

def initialize_compilebot(cb):
    """Reload compilebot module and set necessary method stubs to ensure
    consistency on each test.
    """
    reload(cb)
    cb.LOG_FILE = LOG_FILE
    return cb

def reddit_id(length=6):
    """Emulate a reddit id with a random string of letters and digits"""
    return ''.join(random.choice(string.ascii_lowercase +
                   string.digits) for x in range(length))
