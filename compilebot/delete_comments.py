import praw
import config
import time

"""
A script for deleteing a bunch of comments at once.
"""
def main():
    match_text = "INSERT TEXT HERE"

    r = praw.Reddit(
        user_agent=config.USER_AGENT,
        client_id=config.R_CLIENT_ID,
        client_secret=config.R_CLIENT_SECRET,
        username=config.R_USERNAME,
        password=config.R_PASSWORD,
    )

    user = r.redditor(config.R_USERNAME)
    comments = list(user.comments.new())

    count = 0
    for c in comments:
        if match_text in c.body:
            c.delete()
            count += 1
    print "Comments deleted: {}".format(count)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(10)
