from __future__ import unicode_literals, print_function
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
    details['link'] = sub_link
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
    reply, pm = '', ''
    try:
        args, src, stdin = parse_comment(comment.body)
    except AttributeError:
        label = ("There was an error processing your comment: "
                 "{link}\n\n".format(link=comment.permalink))
        pm = label + ERROR_TEXT
        # TODO send author a PM 
        log("Formatting error on comment {c.id}: {c.body}".format(
            c=comment), alert=True)
        return None, pm
    # Seperate the language name from the rest of the supplied options
    # TODO seperate args and lang in a more robust way
    try:
        lang, opts = args.split(' -', 1)
        opts = ('-' + opts).split()
    except ValueError:
        lang, opts = args, []
    lang = lang.strip()
    try:
        details = compile(src, lang, stdin=stdin)
        log("Compiled ideone submission {link} for {id}".format(
            link=details['link'], id=comment.id))
    except ideone.IdeoneError as e:
        msg = str(e)
        # TODO Add link to accepted languages to msg
        log("Language error on comment {id}".format(id=comment.id))
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
        log("Replied to {id}".format(id=comment.id))
    except praw.errors.RateLimitExceeded as e:
        log('Rate Limit exceeded. '
              'Sleeping for {time} seconds'.format(time=e.sleep_time))
        # Wait and try again.
        time.sleep(e.sleep_time)
        reply_to(comment, text)
    # Handle and log miscellaneous API exceptions
    except praw.errors.APIException as e:
        log("Exception on comment {id}, {error}".format(
            id=comment.id, error=e))

def edit_reply(comment, text):
    comment.edit(text)
    log("Edited comment {}".format(comment.id))

def send_msg(sender, comment, text, subject=''):
    """Reply to a reddit comment via private message."""
    recipient = comment.author
    # If no custom subject line is given, the default will be a label 
    # that identifies the comment.
    if not subject:
        subject = "Comment {}".format(comment.id)
    # Prepend message subject with username
    subject = "{} - {}".format(R_USERNAME, subject)
    sender.send_message(recipient, subject, text)
    log("Message reply for comment {id} sent to {to}".format(
        id=comment.id, to=recipient))
    
def process_inbox(r):
    """Iterate through each unread message/comment in the inbox, parse it
    and reply to it appropriately.
    """
    inbox = r.get_unread()
    for new in inbox:
        sender = new.author
        log("New {type} {id} from {sender}".format(
            type="mention" if new.was_comment else "message",
            id=new.id, sender=sender))
        if sender.name.lower() in BANNED_USERS:
            log("Ignoring banned user {user}".format(user=sender))
            new.mark_as_read()
            continue
        try:
            # Search for a user mention preceded by a '+' which is the signal
            # for CompileBot to create a reply for that comment
            if re.search(r'(?i)\+/u/{}'.format(R_USERNAME), new.body):
                reply, pm = create_reply(new)
                if reply: 
                    reply_to(new, reply) 
                if pm:
                    send_msg(r, new, pm)
            elif ((not new.was_comment) and 
                  re.match(r'(i?)\s*--help', new.body)):
                # Message a user the help text if comment is a message
                # containing "--help".
                send_msg(r, new, HELP_TEXT, subject='Help')
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
                    new.reply("Error recompiling")
                    continue
                # Fetch the comment that will be recompiled.
                sub = r.get_submission(submission_id=id, comment_sort='best')
                original = sub.comments[0]
                log("Processing request to recompile {id} from {user}"
                    "".format(id=original.id, user=new.author))
                # Ensure the author of the original comment matches the author
                # requesting the recompile to prevent one user sending a recompile
                # request on the behalf of another.
                if original.author == new.author:                  
                    reply, pm = create_reply(original)
                    if reply:
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
                                reply += footnote
                                edit_reply(rp, reply)
                                break
                        else:
                            reply_to(original, reply)
                    if pm:
                        send_msg(r, new, pm)
                else:
                    new.reply("Error recompiing. You can only request to "
                              "recompile your own comments.")
                    log("Attempt to reompile on behalf of another author "
                        "detected. Request deined.")
        except:
            tb = traceback.format_exc()
            # Notify admin of any errors
            log("Error processing comment {c.id}\n"
                "{traceback}".format(c=new, traceback=tb), alert=True)
        finally:
            # TODO Mark as read before execution
            new.mark_as_read()  

def main():
    r = praw.Reddit(USER_AGENT)
    r.login(R_USERNAME, R_PASSWORD)
    process_inbox(r)
    
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
if SUBREDDIT:
    # Banned users are taken from the moderator subreddit 
    # banned users list
    r = praw.Reddit(USER_AGENT)
    r.login(R_USERNAME, R_PASSWORD)
    BANNED_USERS = {user.name.lower() for user in 
                    r.get_subreddit(SUBREDDIT).get_banned()}
    del r
else:
    BANNED_USERS = set()
HELP_TEXT = SETTINGS['help_text']
ERROR_TEXT = SETTINGS['error_text']

if __name__ == '__main__':
    main()
