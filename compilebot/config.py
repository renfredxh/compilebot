import yaml

# Configuration
CONFIG_FILE = 'config.yml'

# Fetch settings from YAML file
try:
    with open(CONFIG_FILE, 'r') as f:
        CONFIG = yaml.load(f)
except (OSError, IOError) as e:
    print("Please configure config.yml")
    exit(1)

# File for logging. Default is STDOUT.
LOG_FILE = CONFIG['log_file']

# Login credentials
I_USERNAME = CONFIG['ideone_user']
I_PASSWORD = CONFIG['ideone_pass']
R_USERNAME = CONFIG['reddit_user']
R_PASSWORD = CONFIG['reddit_pass']
USER_AGENT = CONFIG['user_agent']
ADMIN = CONFIG['admin_user']
SUBREDDIT = CONFIG['subreddit']

LANG_SHORTCUTS = {k.lower(): v for k, v in CONFIG['lang_shortcuts'].items()}

# A set of users that are banned. The banned users list is retrieved
# in the main session but not here because it requires a reddit login.
BANNED_USERS = set()

# Text
TEXT = CONFIG['text']
FOOTER = TEXT['footer']
ERROR_PREAMBLE = TEXT['error_preamble']
ERROR_POSTAMBLE = TEXT['error_postamble']
HELP_TEXT = TEXT['help_text']
LANG_ERROR_TEXT = TEXT['language_error_text']
FORMAT_ERROR_TEXT = TEXT['format_error_text']
COMPILE_ERROR_TEXT = TEXT['compile_error_text']
RUNTIME_ERROR_TEXT = TEXT['runtime_error_text']
TIMEOUT_ERROR_TEXT = TEXT['timeout_error_text']
MEMORY_ERROR_TEXT = TEXT['memory_error_text']
ILLEGAL_ERROR_TEXT = TEXT['illegal_error_text']
INTERNAL_ERROR_TEXT =  TEXT['internal_error_text']
RECOMPILE_ERROR_TEXT = TEXT['recompile_error_text']
RECOMPILE_AUTHOR_ERROR_TEXT = TEXT['recompile_author_error_text']

# Spam Settings
LINE_LIMIT = CONFIG['spam']['line_limit']
CHAR_LIMIT = CONFIG['spam']['char_limit']
SPAM_PHRASES = CONFIG['spam']['spam_phrases']
IGNORE_SPAM = CONFIG['spam']['ignore']

