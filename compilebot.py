from __future__ import unicode_literals
import ideone
import time
import praw
import re
import json
import traceback

def log(message, alert=False):
    t = time.strftime('%m-%d %H:%M:%S', time.localtime())
    message = "{}: {}\n".format(t, message)
    with open('compilebot.log', 'a') as f:
        f.write(message)
    if alert:
        # TODO Send message to owner
        pass
    
def compile(source, lang):
    """Execute source using the ideone API and return a dict containing
    the output details""" 
    # Login to ideone and create a submission
    i = ideone.Ideone(USERNAME, PASSWORD)
    sub = i.create_submission(source, language_name=lang)
    sub_link = sub['link']
    details = i.submission_details(sub_link)
    # The status of the submission indicates whether or not the source has
    # finished executing. A status of 0 indicates the submission is finished.
    while details['status'] != 0:
        details = i.submission_details(sub_link)
        time.sleep(3)
    return details

def format_reply(details):
    reply = ''
    if details['output']:
        reply += 'Output:\n'
        output = '\n' + details['output']
        reply += output.replace('\n', '\n    ')
    if details['cmpinfo']:
        reply += 'Compiler Message:\n'
        output = '\n' + details['cmpinfo']
        reply += output.replace('\n', '\n    ')
    return reply

def parse_new(comment):
    c_pattern = r'/u/CompileBot(?P<args>.*)\n\s*\n(?P<source>( {4}.*\n)*( {4}.*))'
    m = re.search(c_pattern, comment.body)
    try:
        args = m.group('args')
        src = m.group('source')
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
    src = src.replace('    ', '', 1)
    src = src.replace('\n    ', '\n')
    details = compile(src, lang)
    return format_reply(details)

def reply_to(comment, text):
    # Truncate message if it exceeds max character limit.
    if len(text) >= 10000:
        text = text[:9995] + '...'
    try:
        comment.reply(text)
        with open('bot.log', 'a') as f:
            f.write(comment.id + '\n')
        log("Replied to {}".format(comment.id))
    except praw.errors.RateLimitExceeded as e:
        log('Rate Limit exceeded. '
              'Sleeping for {} seconds'.format(e.sleep_time))
        # Wait and try again.
        time.sleep(e.sleep_time)
        reply_to(comment, text)
    # Handle and log miscellaneous API exceptions
    except praw.errors.APIException as e:
        with open('bot.log', 'a') as f:
            f.write(comment.id + '\n')
        log("Exception on comment {}, {}".format(comment.id, e))

def process_inbox(r):
    inbox = r.get_unread()
    for new in inbox:
        try:
            reply = parse_new(new)
            if reply: 
                reply_to(new, reply) 
        except:
            # Notify of any errors
            log("Error processing comment {}\n{}".format(new.id, 
                    traceback.format_exc()), alert=True)
        finally:
            # TODO Mark as read before execution
            new.mark_as_read()  

# Fetch settings from json file
try:
    with open('settings.json', 'r') as f:
        SETTINGS = json.load(f)
except (OSError, IOError) as e:
    print("Please configure settings.json")

USERNAME = SETTINGS['ideone_user']
PASSWORD = SETTINGS['ideone_pass']
R_USERNAME = SETTINGS['reddit_user']
R_PASSWORD = SETTINGS['reddit_pass']

def main():
    r = praw.Reddit('Code compilation bot by u/SeaCowVengeance v 0.1.'
                    'url: https://github.com/renfredxh/compilebot')
    r.login(R_USERNAME, R_PASSWORD)
    process_inbox(r)
    
if __name__ == '__main__':
    main()
