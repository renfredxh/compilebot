from __future__ import unicode_literals, print_function
import time
import traceback
from requests import HTTPError, ConnectionError
import compilebot as bot

SLEEP_TIME = 60
ERROR_TIMEOUT = 60 * 4

def main():
    errors = []
    try:
        bot.log("Initializing bot")
        while True:
            try:
                for error in errors:
                    bot.log(error, alert=True)
                bot.main()
            except HTTPError as e:
                # HTTP Errors may indicate reddit is overloaded.
                # Sleep for some extra time. 
                bot.log(str(e) + " ")
                time.sleep(ERROR_TIMEOUT)
            except ConnectionError as e:
                bot.log(str(e) + " ")
                time.sleep(ERROR_TIMEOUT)
            except Exception as e:
                tb = traceback.format_exc()
                # If another exception occurs, add the message to a buffer so
                # it can be sent to the admins in the try block above.
                # Otherwise the bot.log method may cause another error that
                # won't be caught.
                error_msg = "Error running bot.main:\n{error}".format(
                    error=bot.code_block(tb))
                # Avoid adding duplicates.
                if len(errors) == 0 or errors[-1] != error_msg:
                    errors.append(error_msg)
                time.sleep(ERROR_TIMEOUT)
            time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        exit_msg = ''
        exit(0)
    except Exception as e:
        tb = traceback.format_exc()
        exit_msg = "Depoyment error:\n{traceback}\n".format(
            traceback=bot.code_block(tb))
        bot.log("{msg}Bot shutting down".format(msg=exit_msg), alert=True)
        exit(1)

if __name__ == "__main__":
    main()
