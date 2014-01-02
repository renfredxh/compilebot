from __future__ import unicode_literals, print_function
import ideone
import time
import praw
import re
import json
import traceback

class Reply(object):
    
    """An object that represents a potential response to a comment.
    
    Replies are not tied to a specific recipient on at their inception,
    however once sent the recipient should be recorded.
    """
    
    def __init__(self, text):
        # Truncate text if it exceeds max character limit.
        if len(text) >= 10000:
            text = text[:9995] + '\n...'
        self.text = text
        self.recipient = None
    
    def send(self, *args, **kwargs):
        """An abstract method that sends the reply."""
        raise NotImplementedError
            
class CompiledReply(Reply):
    
    """Replies that contain details about evaluated code. These can be 
    sent as replies to comments.
    
    """
    def __init__(self, text, compile_details):
        Reply.__init__(self, text)
        self.compile_details = compile_details
        self.parent_comment = None
        
    def send(self, comment, r=None):
        """Send a reply to a specific reddit comment or message."""
        self.parent_comment = comment
        self.recipient = comment.author
        try:
            comment.reply(self.text)
            log("Replied to {id}".format(id=comment.id))
        except praw.errors.RateLimitExceeded as e:
            log('Rate Limit exceeded. '
                'Sleeping for {time} seconds'.format(time=e.sleep_time))
            # Wait and try again.
            time.sleep(e.sleep_time)
            self.send(comment)
        # Handle and log miscellaneous API exceptions
        except praw.errors.APIException as e:
            log("Exception on comment {id}, {error}".format(
                id=comment.id, error=e))
                
    def make_edit(self, comment, parent):
        """Edit one of the bot's existing comments."""
        self.parent_comment = parent
        self.recipient = parent.author
        comment.edit(self.text)
        log("Edited comment {}".format(comment.id))
        
    def detect_spam(self):
        """Scan a reply and return a list of potentially spammy attributes
        found in the comment's output.
         """
        output = self.compile_details['output']
        source = self.compile_details['source']
        errors = self.compile_details['stderr']
    
        spam_behaviors = {
            "Excessive line breaks": output.count('\n') > LINE_LIMIT,
            "Excessive character count": len(output) > CHAR_LIMIT,
            "Spam phrase detected": any([word in (source + output).lower()
                                         for word in SPAM_PHRASES]),
            "Illegal system call detected": "Permission denied" in errors
        }
        if any(spam_behaviors.values()):
            spam_triggers = [k for k, v in spam_behaviors.iteritems() if v]
            return spam_triggers
        return []

class MessageReply(Reply):

    """Replies that contain information that may be sent to a reddit user
    via private message. 
    """
    
    def __init__(self, text, subject=''):
        Reply.__init__(self, text)
        self.subject = subject

    def send(self, comment, r):
        """Reply the author of a reddit comment by sending them a reply
        via private message.
        """
        self.recipient = comment.author
        # If no custom subject line is given, the default will be a label
        # that identifies the comment.
        if not self.subject:
            self.subject = "Comment {}".format(comment.id)
        # Prepend message subject with username
        self.subject = "{} - {}".format(R_USERNAME, self.subject)
        r.send_message(self.recipient, self.subject, self.text)
        log("Message reply for comment {id} sent to {to}".format(
            id=comment.id, to=self.recipient))

def log(message, alert=False):
    """Log messages along with a timestamp in a log file. If the alert
    option is set to true, send a message to the admin's reddit inbox.
    """
    t = time.strftime('%y-%m-%d %H:%M:%S', time.localtime())
    message = "{}: {}\n".format(t, message)
    print(message, end='')
    if LOG_FILE:
        with open(LOG_FILE, 'a') as f:
            f.write(message)
    if alert and ADMIN:
        r = praw.Reddit(USER_AGENT)
        r.login(R_USERNAME, R_PASSWORD)
        # Indent text as markdown block for readability
        admin_alert = code_block(message)
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
    details['link'] = sub_link
    return details

def code_block(text):
    """Create a markdown formatted code block containing the given text"""
    return ('\n' + text).replace('\n', '\n    ')
    
def get_banned(r):
    """Retrive list of banned users list from the moderator subreddit"""
    # Banned users are taken from the moderator subreddit 
    # banned users list
    banned = {user.name.lower() for user in 
                    r.get_subreddit(SUBREDDIT).get_banned()}
    return banned

def format_reply(details, opts):
    """Returns a reply that contains the output from a ideone submission's 
    details along with optional additional information.
    """
    head, body, extra, footer = '', '', '', ''
    # Combine information that will go before the output
    if '--source' in opts:
        head += 'Source:\n\n{}\n'.format(code_block(details['source']))
    if '--input' in opts:
    # Combine program output and runtime error output
        head += 'Input:\n\n{}\n'.format(code_block(details['input']))
    output = details['output'] + details['stderr']
    # Truncate the output if it contains an excessive 
    # amount of line breaks or if it is too long.
    if output.count('\n') > 100:
        lines = output.split('\n')
        output = '\n'.join(lines[:101])
        output += "\n..."
    # Truncate the output if it is too long.
    if len(output) > 8000:
        output = output[:8000] + '\n    ...\n'
    body += 'Output:\n\n{}\n'.format(code_block(output))
    if details['cmpinfo']:
        body += 'Compiler Info:\n\n{}\n'.format(code_block(details['cmpinfo']))
    # Combine extra runtime information
    if '--date' in opts:
        extra += "Date: {}\n\n".format(details['date'])
    if '--memory' in opts:
        extra += "Memory Usage: {}\n\n".format(details['memory'])
    if '--time' in opts:
        extra += "Execution Time: {} seconds\n\n".format(details['time'])
    if '--version' in opts:
        extra += "Version: {}\n\n".format(details['langVersion'])
    # To ensure the reply is less than 10000 characters long, shorten
    # sections of the reply until they are of adequate length. Certain
    # sections with less priority will be shorted before others.
    reply_text = ''
    for section in (body, head, extra):
        if len(section) + len(reply_text) > 9800:
            section = section[:9800 - len(reply_text)] + '\n...\n'
        reply_text += section 
    reply_text += footer
    return reply_text

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
        r'\+/u/(?i)%s\s*(?P<args>.*)\n\s*'
        r'(?<=\n {4})(?P<src>.*(\n( {4}.*\n)*( {4}.*))?)'
        r'(\n\s*((?i)Input|Stdin):?\s*\n\s*'
        r'(?<=\n {4})(?P<in>.*(\n( {4}.*\n)*( {4}.*\n?))?))?'
    ) % R_USERNAME
    m = re.search(c_pattern, body)
    args, src, stdin = m.group('args'), m.group('src'), m.group('in') or ''
    # Remove the leading four spaces from every line
    src = src.replace('\n    ', '\n')
    stdin = stdin.replace('\n    ', '\n')
    return args, src, stdin
    
def create_reply(comment):
    """Search comments for username mentions followed by code blocks
    and return a formatted reply containing the output of the executed
    block or a message with additional information.
    """  
    try:
        args, src, stdin = parse_comment(comment.body)
    except AttributeError:
        preamble = ERROR_PREAMBLE.format(link=comment.permalink)
        postamble = ERROR_POSTAMBLE.format(link=comment.permalink)
        reply = preamble + FORMAT_ERROR_TEXT + postamble
        # TODO send author a PM 
        log("Formatting error on comment {c.id}: {c.body}".format(
            c=comment), alert=True)
        return MessageReply(reply)
    # Seperate the language name from the rest of the supplied options
    # TODO seperate args and lang in a more robust way
    try:
        lang, opts = args.split(' -', 1)
        opts = ('-' + opts).split()
    except ValueError:
        # No additional opts found
        lang, opts = args, []
    lang = lang.strip()
    try:
        details = compile(src, lang, stdin=stdin)
        log("Compiled ideone submission {link} for comment {id}".format(
            link=details['link'], id=comment.id))
    except ideone.LanguageNotFoundError as e:
        preamble = ERROR_PREAMBLE.format(link=comment.permalink)
        postamble = ERROR_POSTAMBLE.format(link=comment.permalink)
        choices = ', '.join(e.similar_languages)
        error_reply = ("The language you requested (\"{lang}\"), was not "
                       "found. Perhaps you meant one of the following: "
                       "{choices}").format(lang=lang, choices=choices)
        error_reply = preamble + error_reply + postamble
        # TODO Add link to accepted languages to msg
        log("Language error on comment {id}".format(id=comment.id))
        return MessageReply(error_reply)
    # The ideone submission result value indicaties the final state of
    # the program. If the program compiled and ran successfully the 
    # result is 15. Other codes indicate various errors.
    result_code = details['result'] 
    # The user is alerted of any errors via message reply unless they
    # include an option to include errors in the reply
    if result_code == 15 or '--include-errors' in opts:
        text = format_reply(details, opts)
    else:
        log("Result error {code} detected in comment {id}".format(
            code=result_code, id=comment.id))
        preamble = ERROR_PREAMBLE.format(link=comment.permalink)
        postamble = ERROR_POSTAMBLE.format(link=comment.permalink)
        error_reply = {
            11: COMPILE_ERROR_TEXT,
            12: RUNTIME_ERROR_TEXT,
            13: TIMEOUT_ERROR_TEXT,
            17: MEMORY_ERROR_TEXT,
            19: ILLEGAL_ERROR_TEXT,
            20: INTERNAL_ERROR_TEXT          
        }.get(result_code, '')
        # Include any output from the submission in the reply
        if details['cmpinfo']:
            error_reply += "Compiler Output:\n\n{}\n\n".format(
                                code_block(details['cmpinfo']))
        if details['output']:
            error_reply += "Output:\n\n{}\n\n".format(
                    code_block(details['cmpinfo']))                
        if details['stderr']:
            error_reply += "Error Output:\n\n{}\n\n".format(
                                code_block(details['stderr']))
        error_reply = preamble + error_reply + postamble
        return MessageReply(error_reply)
    return CompiledReply(text, details)
    
def process_inbox(new, r):
    """Parse a new comment or message for various options and ignore reply 
    to as appropriate.
    """
    sender = new.author
    log("New {type} {id} from {sender}".format(
        type="mention" if new.was_comment else "message",
        id=new.id, sender=sender))
    if sender.name.lower() in BANNED_USERS:
        log("Ignoring banned user {user}".format(user=sender))
        return
    # Search for a user mention preceded by a '+' which is the signal
    # for CompileBot to create a reply for that comment
    if (new.was_comment and 
        re.search(r'(?i)\+/u/{}'.format(R_USERNAME), new.body)):
        reply = create_reply(new)
        if reply: 
            reply.send(new, r)
    elif ((not new.was_comment) and 
          re.match(r'(i?)\s*--help', new.body)):
        # Message a user the help text if comment is a message
        # containing "--help".
        reply = MessageReply(HELP_TEXT, subject='Help')
        reply.send(new, r)
    elif ((not new.was_comment) and 
          re.match(r'(i?)\s*--recompile', new.body)):
        # Search for the recompile command followed by a comment id.
        # Example: 1tt4jt/post_title/ceb7czt
        # The comment id can optionally be prefixed by a url.
        # Example: reddit.com/r/sub/comments/1tt4jt/post_title/ceb7czt
        p = (r'(i?)--recompile\s*(?P<url>[^\s*]+)?'
             r'(?P<id>\b\w+/\w+/\w+\b)')
        m = re.search(p, new.body)
        try:
            id = m.group('id')
        except AttributeError:
            new.reply(RECOMPILE_ERROR_TEXT)
        # Fetch the comment that will be recompiled.
        sub = r.get_submission(submission_id=id, comment_sort='best')
        original = sub.comments[0]
        log("Processing request to recompile {id} from {user}"
            "".format(id=original.id, user=new.author))
        # Ensure the author of the original comment matches the author
        # requesting the recompile to prevent one user sending a recompile
        # request on the behalf of another.
        if original.author == new.author:                  
            reply = create_reply(original)
            # Ensure the recompiled reply resulted in a valid comment
            # reply and not an error message reply.
            if isinstance(reply, CompiledReply):
                # Search for an existing comment reply from the bot.
                # If one is found, edit the existing comment instead
                # of creating a new one. 
                #
                # Note: the .replies property only returns a limited
                # number of comments. If the reply is buried, it will
                # not be retrieved and a new one will be created
                for rp in original.replies:
                    if rp.author.name.lower() == R_USERNAME.lower():
                        footnote = ("\n\n**EDIT:** Recompile request "
                                    "by {}".format(new.author))
                        reply.text += footnote
                        reply.make_edit(rp, original)
                        break
                else:
                    reply.send(original)
            else:
                reply.send(new, r)
        else:
            new.reply("Error recompiing. You can only request to "
                      "recompile your own comments.")
            log("Attempt to reompile on behalf of another author "
                "detected. Request deined.")
    if isinstance(reply, CompiledReply):
        spam = reply.detect_spam()
        if spam:
            text = ("Potential spam detected on comment {c.permalink} "
                    "by {c.author}: ".format(c=reply.parent_comment))
            text += ', '.join(spam)
            log(text, alert=True)
        
def main():
    r = praw.Reddit(USER_AGENT)
    r.login(R_USERNAME, R_PASSWORD)
    if SUBREDDIT:
        global BANNED_USERS
        BANNED_USERS = get_banned(r)
    # Iterate though each new comment/message in the inbox and
    # process it appropriately
    inbox = r.get_unread()
    for new in inbox:
        try:
            process_inbox(new, r)
        except:
            tb = traceback.format_exc()
            # Notify admin of any errors
            log("Error processing comment {c.id}\n"
                "{traceback}".format(c=new, traceback=tb), alert=True)
        finally:
            new.mark_as_read()
            
# Settings
LOG_FILE = '../compilebot.log'
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
ADMIN = None#SETTINGS['admin_user']
SUBREDDIT = SETTINGS['subreddit']
# A set of users that are banned. The banned users list is retrieved
# in the main session but not here because it requires a reddit login.
BANNED_USERS = set()
# Text
TEXT = SETTINGS['text']
ERROR_PREAMBLE = "There was an error processing your comment: {link}\n\n"
ERROR_POSTAMBLE = ("You can edit your original comment and have it "
                  "recompiled by replying to this message with the following: "
                  "\n\n--recompile {link}")
HELP_TEXT = TEXT['help_text']
FORMAT_ERROR_TEXT = TEXT['format_error_text']
COMPILE_ERROR_TEXT = TEXT['compile_error_text']
RUNTIME_ERROR_TEXT = TEXT['runtime_error_text']
TIMEOUT_ERROR_TEXT = TEXT['timeout_error_text']
MEMORY_ERROR_TEXT = TEXT['memory_error_text']
ILLEGAL_ERROR_TEXT = TEXT['illegal_error_text']
INTERNAL_ERROR_TEXT =  TEXT['internal_error_text']
RECOMPILE_ERROR_TEXT = TEXT['recompile_error_text']
# Spam Settings
LINE_LIMIT = SETTINGS["spam"]["line_limit"]
CHAR_LIMIT = SETTINGS["spam"]["char_limit"]
SPAM_PHRASES = SETTINGS["spam"]["spam_phrases"]

if __name__ == '__main__':
    main()
