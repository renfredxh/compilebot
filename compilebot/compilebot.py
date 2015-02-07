from __future__ import unicode_literals, print_function
import ideone
import time
import praw
import re
import urllib
import traceback
from socket import error as SocketError
from sys import exit
from functools import wraps
from config import *

def handle_api_exceptions(max_attempts=1):
    """Return a function decorator that wraps a given function in a
    try-except block that will handle various exceptions that may
    occur during an API request to reddit. A maximum number of retry 
    attempts may be specified.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_attempts:
                sleep_time = None
                error_msg = ""
                try:
                    return func(*args, **kwargs)
                except praw.errors.RateLimitExceeded as e:
                    error_msg = "Rate Limit exceeded"
                    sleep_time = e.sleep_time
                except praw.requests.HTTPError as e:
                    error_msg = "HTTPError \"{error}\" occurred: ".format(
                        error=e)
                    # Quit when encountering an HTTP 403 "Forbidden" errors.
                    if '403' in str(e):
                        log(error_msg)
                        return
                # Handle and log miscellaneous API exceptions
                except praw.errors.APIException as e:
                    error_msg = "API Exception \"{error}\" occurred: ".format(
                        error=e)
                except SocketError as e:
                    error_msg = "SocketError \"{error}\" occurred: ".format(
                        error=e)
                    log(error_msg)
                sleep_time = sleep_time or retries * 150
                log("{0} in {f}. Sleeping for {t} seconds. "
                    "Attempt {rt} of {at}.".format(error_msg, f=func.__name__,
                        t=sleep_time, rt=retries+1, at=max_attempts))
                time.sleep(sleep_time)
                retries += 1
        return wrapper
    return decorator

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

    @handle_api_exceptions(max_attempts=3)
    def send(self, comment):
        """Send a reply to a specific reddit comment or message."""
        self.parent_comment = comment
        self.recipient = comment.author
        comment.reply(self.text)
        log("Replied to {id}".format(id=comment.id))

    @handle_api_exceptions(max_attempts=3)
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
            "Spam phrase detected": any([word.encode('utf-8').lower() in
                                         (source + output).encode('utf-8').lower()
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

    @handle_api_exceptions(max_attempts=3)
    def send(self, comment):
        """Reply the author of a reddit comment by sending them a reply
        via private message.
        """
        self.recipient = comment.author
        r = comment.reddit_session
        # If no custom subject line is given, the default will be a label
        # that identifies the comment.
        if not self.subject:
            self.subject = "Comment {id}".format(id=comment.id)
        # Prepend message subject with username
        self.subject = "{} - {}".format(R_USERNAME, self.subject)
        r.send_message(self.recipient, self.subject, self.text)
        log("Message reply for comment {id} sent to {to}".format(
            id=comment.id, to=self.recipient))

@handle_api_exceptions(max_attempts=3)
def log(message, alert=False):
    """Log messages along with a timestamp in a log file. If the alert
    option is set to true, send a message to the admin's reddit inbox.
    """
    t = time.strftime('%y-%m-%d %H:%M:%S', time.localtime())
    message = "{}: {}\n".format(t, message)
    if LOG_FILE:
        with open(LOG_FILE, 'a') as f:
            f.write(message)
    else:
        print(message, end='')
    if alert and ADMIN:
        r = praw.Reddit(USER_AGENT)
        r.login(R_USERNAME, R_PASSWORD)
        admin_alert = message
        subject = "CompileBot Alert"
        r.send_message(ADMIN, subject, admin_alert)

@handle_api_exceptions(max_attempts=3)
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
    lang = LANG_ALIASES.get(lang.lower(), lang)
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
    text = '\n' + text
    for char in ['\n', '\r']:
        text = text.replace(char, '\n    ')
    return text

@handle_api_exceptions()
def get_banned(reddit):
    """Retrive list of banned users list from the moderator subreddit"""
    banned = {user.name.lower() for user in
                reddit.get_subreddit(SUBREDDIT).get_banned()}
    return banned

@handle_api_exceptions()
def send_modmail(subject, body, reddit):
    """Send a message to the bot moderators"""
    if SUBREDDIT:
        sub = reddit.get_subreddit(SUBREDDIT)
        reddit.send_message(sub, subject, body)
    else:
        log("Mod message not sent. No subreddit found in settings.")

def format_reply(details, opts):
    """Returns a reply that contains the output from a ideone submission's
    details along with optional additional information.
    """
    head, body, extra, = '', '', ''
    # Combine information that will go before the output.
    if '--source' in opts:
        head += 'Source:\n{}\n\n'.format(code_block(details['source']))
    if '--input' in opts:
    # Combine program output and runtime error output.
        head += 'Input:\n{}\n\n'.format(code_block(details['input']))
    output = details['output'] + details['stderr']
    # Truncate the output if it contains an excessive
    # amount of line breaks or if it is too long.
    if output.count('\n') > LINE_LIMIT:
        lines = output.split('\n')
        # If message contains an excessive amount of duplicate lines,
        # truncate to a small amount of lines to discourage spamming
        if len(set(lines)) < 5:
            lines_allowed = 2
        else:
            lines_allowed = 51
        output = '\n'.join(lines[:lines_allowed])
        output += "\n..."
    # Truncate the output if it is too long.
    if len(output) > 8000:
        output = output[:8000] + '\n    ...\n'
    body += 'Output:\n{}\n\n'.format(code_block(output))
    if details['cmpinfo']:
        body += 'Compiler Info:\n{}\n\n'.format(code_block(details['cmpinfo']))
    # Combine extra runtime information.
    if '--date' in opts:
        extra += "Date: {}\n\n".format(details['date'])
    if '--memory' in opts:
        extra += "Memory Usage: {} bytes\n\n".format(details['memory'])
    if '--time' in opts:
        extra += "Execution Time: {} seconds\n\n".format(details['time'])
    if '--version' in opts:
        extra += "Version: {}\n\n".format(details['langVersion'])
    # To ensure the reply is less than 10000 characters long, shorten
    # sections of the reply until they are of adequate length. Certain
    # sections with less priority will be shortened before others.
    total_len = 0
    for section in (FOOTER, body, head, extra):
        if len(section) + total_len > 9800:
            section = section[:9800 - total_len] + '\n...\n'
            total_len += len(section)
    reply_text = head + body + extra
    return reply_text

def parse_comment(body):
    """Parse a string that contains a username mention and code block
    and return the supplied arguments, source code and input.

    c_pattern is a regular expression that searches for the following:
        1. "+/u/" + the reddit username that is using the program
            (case insensitive).
        2. A string representing the programming language and arguments
            + a "\n".
        3. A markdown code block (one or more lines indented by 4 spaces or
            a tab) that represents the source code + a "\n".
        4. (Optional) "Input:" OR "Stdin:" + "\n".
        5. (Optional) A markdown code block that represents the
            program's input.
    """
    c_pattern = (
        r'\+/u/(?i)%s\s*(?P<args>.*)\n\s*'
        r'((?<=\n( {4}))|(?<=\n\t))'
        r'(?P<src>.*(\n((( {4}|\t).*\n)|\n)*(( {4}|\t).*))?)'
        r'(\n\s*((?i)Input|Stdin):?\s*\n\s*'
        r'((?<=\n( {4}))|(?<=\n\t))'
        r'(?P<in>.*(\n((( {4}|\t).*\n)|\n)*(( {4}|\t).*\n?))?))?'
    ) % R_USERNAME
    m = re.search(c_pattern, body)
    args, src, stdin = m.group('args'), m.group('src'), m.group('in') or ''
    # Remove the leading four spaces from every line.
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
        error_text = preamble + FORMAT_ERROR_TEXT + postamble
        log("Formatting error on comment {c.permalink}:\n\n{c.body}".format(
            c=comment))
        return MessageReply(error_text)
    # Seperate the language name from the rest of the supplied options.
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
        error_text = LANG_ERROR_TEXT.format(lang=lang, choices=choices)
        error_text = preamble + error_text + postamble
        # TODO Add link to accepted languages to msg
        log("Language error on comment {id}".format(id=comment.id))
        return MessageReply(error_text)
    # The ideone submission result value indicaties the final state of
    # the program. If the program compiled and ran successfully the
    # result is 15. Other codes indicate various errors.
    result_code = details['result']
    # The user is alerted of any errors via message reply unless they
    # include an option to include errors in the reply.
    if result_code == 15 or ('--include-errors' in opts and result_code in [11, 12]):
        text = format_reply(details, opts)
        ideone_link = "http://ideone.com/{}".format(details['link'])
        url_pl = urllib.quote(comment.permalink)
        text += FOOTER.format(ide_link=ideone_link, perm_link=url_pl)
    else:
        log("Result error {code} detected in comment {id}".format(
            code=result_code, id=comment.id))
        preamble = ERROR_PREAMBLE.format(link=comment.permalink)
        postamble = ERROR_POSTAMBLE.format(link=comment.permalink)
        error_text = {
            11: COMPILE_ERROR_TEXT,
            12: RUNTIME_ERROR_TEXT,
            13: TIMEOUT_ERROR_TEXT,
            17: MEMORY_ERROR_TEXT,
            19: ILLEGAL_ERROR_TEXT,
            20: INTERNAL_ERROR_TEXT
        }.get(result_code, '')
        # Include any output from the submission in the reply.
        if details['cmpinfo']:
            error_text += "Compiler Output:\n\n{}\n\n".format(
                                code_block(details['cmpinfo']))
        if details['output']:
            error_text += "Output:\n\n{}\n\n".format(
                    code_block(details['output']))
        if details['stderr']:
            error_text += "Error Output:\n\n{}\n\n".format(
                                code_block(details['stderr']))
        error_text = preamble + error_text + postamble
        return MessageReply(error_text)
    return CompiledReply(text, details)

@handle_api_exceptions()
def process_unread(new, r):
    """Parse a new comment or message for various options and ignore reply
    to as appropriate.
    """
    reply = None
    sender = new.author
    log("New {type} {id} from {sender}".format(
        type="mention" if new.was_comment else "message",
        id=new.id, sender=sender))
    if sender.name.lower() in BANNED_USERS:
        log("Ignoring banned user {user}".format(user=sender))
        return
    # Search for a user mention preceded by a '+' which is the signal
    # for CompileBot to create a reply for that comment.
    if (new.was_comment and
        re.search(r'(?i)\+/u/{}'.format(R_USERNAME), new.body)):
        reply = create_reply(new)
        if reply:
            reply.send(new)
    elif ((not new.was_comment) and
          re.match(r'(i?)\s*--help', new.body)):
        # Message a user the help text if comment is a message
        # containing "--help".
        reply = MessageReply(HELP_TEXT, subject='CompileBot Help')
        reply.send(new)
    elif ((not new.was_comment) and
          re.match(r'(i?)\s*--report', new.body) and SUBREDDIT):
        # Forward a reported message to the moderators.
        send_modmail("Report from {author}".format(author=new.author),
                     new.body, r)
        reply = MessageReply("Your message has been forwarded to the "
                             "moderators. Thank you.",
                             subject="CompileBot Report")
        reply.send(new)
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
            return
        # Fetch the comment that will be recompiled.
        sub = r.get_submission(submission_id=id, comment_sort='best')
        try:
            original = sub.comments[0]
        except IndexError:
            # In case the comment is deleted
            return
        log("Processing request to recompile {id} from {user}"
            "".format(id=original.id, user=new.author))
        # Ensure the author of the original comment matches the author
        # requesting the recompile to prevent one user sending a recompile
        # request on the behalf of another.
        if original.author == new.author:
            reply = create_reply(original)
        else:
            new.reply(RECOMPILE_AUTHOR_ERROR_TEXT)
            log("Attempt to reompile on behalf of another author "
                "detected. Request deined.")
            return
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
                # Reply to the original comment.
                reply.send(original)
        else:
            # Send a message reply.
            reply.send(new)
    if reply and isinstance(reply, CompiledReply):
        # Report any potential spam to the moderators.
        spam = reply.detect_spam()
        if spam and reply.parent_comment.subreddit.display_name not in IGNORE_SPAM:
            text = ("Potential spam detected on comment {c.permalink} "
                    "by {c.author}: ".format(c=reply.parent_comment))
            text += ', '.join(spam)
            send_modmail("Potential spam detected", text, r)
            log(text)

@handle_api_exceptions()
def main():
    r = praw.Reddit(USER_AGENT)
    r.login(R_USERNAME, R_PASSWORD)
    if SUBREDDIT:
        global BANNED_USERS
        BANNED_USERS = get_banned(r)
    # Iterate though each new comment/message in the inbox and
    # process it appropriately.
    inbox = r.get_unread()
    for new in inbox:
        try:
            process_unread(new, r)
        except:
            tb = traceback.format_exc()
            # Notify admin of any errors
            log("Error processing comment {c.id}\n"
                "{traceback}".format(c=new, traceback=tb), alert=True)
        finally:
            new.mark_as_read()

if __name__ == "__main__":
    main()
