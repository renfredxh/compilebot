from __future__ import unicode_literals
import ideone
import time
import praw
import re
import json
import traceback

def log(message, alert=False):
    """Log messages along with a timestamp in a log file. If the alert
    option is set to true, send a message to the admin's reddit inbox.
    """
    if not LOG_FILE:
        return
    t = time.strftime('%m-%d %H:%M:%S', time.localtime())
    message = "{}: {}\n".format(t, message)
    with open(LOG_FILE, 'a') as f:
        f.write(message)
    if alert and ADMIN:
        r = praw.Reddit(USER_AGENT)
        r.login(R_USERNAME, R_PASSWORD)
        # Indent text as markdown block for readability
        admin_alert = ('\n' + message).replace('\n', '\n    ')
        subject = "CompileBot Alert"
        r.send_message(ADMIN, subject, admin_alert)
    
def compile(source, lang, stdin=''):
    """Compile and evaluate source sode using the ideone API and return
    a dict containing the output details.
    
    Keyword arguments:
    source -- a string containing source code to be compiled and evaluated
    lang -- the programming language pertaining to the source code
    stdin -- optional "standard input" for the program
    
    >>> d = compile('print("Hello World")', 'python')
    >>> d['output']
    Hello World

    """ 
    # Login to ideone and create a submission
    i = ideone.Ideone(I_USERNAME, I_PASSWORD)
    sub = i.create_submission(source, language_name=lang, std_input=stdin)
    sub_link = sub['link']
    details = i.submission_details(sub_link)
    # The status of the submission indicates whether or not the source has
    # finished executing. A status of 0 indicates the submission is finished.
    while details['status'] != 0:
        details = i.submission_details(sub_link)
        time.sleep(3)
    return details

def format_reply(details, opts):
    """Returns a reply that contains the output from a ideone submission's 
    details along with optional additional information.
    """
    reply = ''
    if '--source' in opts:
        reply += 'Source:\n\n{}\n'.format(
            ('\n' + details['source']).replace('\n', '\n    '))
    if '--input' in opts:
        reply += 'Input:\n\n{}\n'.format(
            ('\n' + details['input']).replace('\n', '\n    '))
    # Combine program output and runtime error output
    output = details['output'] + details['stderr']
    reply += 'Output:\n\n{}\n'.format(
        ('\n' + output).replace('\n', '\n    '))
    if details['cmpinfo']:
        reply += 'Compiler Message:\n\n{}\n\n'.format(
            details['cmpinfo'].replace('\n', '\n    '))
    if '--date' in opts:
        reply += "Date: {}\n\n".format(details['date'])
    if '--memory' in opts:
        reply += "Memory Usage: {}\n\n".format(details['memory'])
    if '--time' in opts:
        reply += "Execution Time: {} seconds\n\n".format(details['time'])
    if '--version' in opts:
        reply += "Version: {}\n\n".format(details['langVersion']) 
    return reply

def parse_comment(body):
    """Parse a string that contains a username mention and code block
    and return the supplied arguments, source code and input.
    
    c_pattern is a regular expression that searches for the following:
        1. "+/u/" + the reddit username that is using the program 
            (case insensitive).
        2. A string representing the programming language and arguments 
            + a "\n".
        3. A markdown code block (one or more lines indented by 4 spaces)
            that represents the source code + a "\n".
        4. (Optional) "Input:" OR "Stdin:" + "\n".
        5. (Optional) A markdown code block that represents the
            program's input.
    """
    c_pattern = (
        r'\+/u/(?i)%s(?P<args>.*)\n\s*'
        r'(?<=\n {4})(?P<src>.*(\n( {4}.*\n)*( {4}.*))?)'
        r'(\n\s*((?i)Input|Stdin):?\n\s*'
        r'(?<=\n {4})(?P<in>.*(\n( {4}.*\n)*( {4}.*\n?))?))?'
    ) % R_USERNAME
    m = re.search(c_pattern, body)
    args, src, stdin = m.group('args'), m.group('src'), m.group('in') or ''
    return args, src, stdin
    
def create_reply(comment):
    """Search comments for username mentions followed by code blocks
    and return a formatted reply containing the output of the executed
    block or a message with additional information.
    """  
    reply, pm = '', ''
    # Message a user the help text if "--help" is the first argument
    if re.match(r'(?i)\+/u/{}\s*--help'.format(R_USERNAME), comment.body):
        return None, HELP_TEXT
    try:
        args, src, stdin = parse_comment(comment.body)
    except AttributeError:
        pm = "There was an error processing your comment."
        # TODO send author a PM 
        log("Formatting error on comment {}".format(comment.id))
        return None, pm
    # Seperate the language name from the rest of the supplied options
    # TODO seperate args and lang in a more robust way
    try:
        lang, opts = args.split(' -', 1)
        opts = ('-' + opts).split()
    except ValueError:
        lang, opts = args, []
    lang = lang.strip()
    # Remove the leading four spaces from every line
    src = src.replace('\n    ', '\n')
    stdin = stdin.replace('\n    ', '\n')
    try:
        details = compile(src, lang, stdin=stdin)
    except ideone.IdeoneError as e:
        msg = str(e)
        # TODO Add link to accepted languages to msg
        log("Language error on comment {}".format(comment.id))
        return None, msg
    reply = format_reply(details, opts)
    return reply, pm

def reply_to(comment, text):
    """Reply to a reddit comment using the supplied text"""
    # Truncate message if it exceeds max character limit.
    if len(text) >= 10000:
        text = text[:9995] + '...'
    try:
        comment.reply(text)
        log("Replied to {}".format(comment.id))
    except praw.errors.RateLimitExceeded as e:
        log('Rate Limit exceeded. '
              'Sleeping for {} seconds'.format(e.sleep_time))
        # Wait and try again.
        time.sleep(e.sleep_time)
        reply_to(comment, text)
    # Handle and log miscellaneous API exceptions
    except praw.errors.APIException as e:
        log("Exception on comment {}, {}".format(comment.id, e))

def process_inbox(r):
    """Iterate through each unread message/comment in the inbox, parse it
    and reply to it appropriately.
    """
    inbox = r.get_unread()
    for new in inbox:
        try:
            if re.match(r'(?i)\+/u/{}'.format(R_USERNAME), new.body):
                reply, pm = create_reply(new)
                if reply: 
                    reply_to(new, reply) 
                if pm:
                    reply_msg(r, new, pm)
        except:
            # Notify admin of any errors
            log("Error processing comment {}\n{}".format(new.id, 
                    traceback.format_exc()), alert=True)
        finally:
            # TODO Mark as read before execution
            new.mark_as_read()  

# Settings
LOG_FILE = 'compilebot.log'
SETTINGS_FILE = 'settings.json'
# Fetch settings from json file
try:
    with open(SETTINGS_FILE, 'r') as f:
        SETTINGS = json.load(f)
except (OSError, IOError) as e:
    print("Please configure settings.json")
# Login credentials
I_USERNAME = SETTINGS['ideone_user']
I_PASSWORD = SETTINGS['ideone_pass']
R_USERNAME = SETTINGS['reddit_user']
R_PASSWORD = SETTINGS['reddit_pass']
USER_AGENT = SETTINGS['user_agent']
ADMIN = SETTINGS['admin_user']
HELP_TEXT = SETTINGS['help_text']

def main():
    r = praw.Reddit(USER_AGENT)
    r.login(R_USERNAME, R_PASSWORD)
    process_inbox(r)
    
if __name__ == '__main__':
    main()
