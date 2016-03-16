from __future__ import unicode_literals, print_function
import time
import traceback
from requests import HTTPError, ConnectionError
import compilebot as bot

SLEEP_TIME = 60
ERROR_TIMEOUT = 60
ERROR_LIMIT = 5

def main():
    errors, log_buffer = {}, []
    try:
        bot.log("Initializing bot")
        while True:
            try:
                for error in log_buffer:
                    bot.log(error, alert=True)
                log_buffer = []
                bot.main()
                errors = {}
                time.sleep(SLEEP_TIME)
            except HTTPError as e:
                # HTTP Errors may indicate reddit is overloaded.
                # Sleep for some extra time. 
                bot.log(str(e) + " ")
                time.sleep(ERROR_TIMEOUT)
            except ConnectionError as e:
                bot.log(str(e) + " ")
                time.sleep(ERROR_TIMEOUT)
            except Exception as e:
                error = str(e) or repr(e)
                if errors.get(error):
                    errors[error] += 1
                    if errors[error] >= ERROR_LIMIT:
                        bot.log("Encounted error of type \"{}\" {} times in a row, "
                                "bot shutting down".format(error, ERROR_LIMIT))
                        exit(1)
                    bot.log("Error running bot.main: {} ({}/{})".format(error,
                            errors[error], ERROR_LIMIT))
                else:
                    errors[error] = 1
                    # If another exception occurs, add the message to a buffer so
                    # it can be sent to the admins in the try block above.
                    # Otherwise the bot.log method may cause another error that
                    # won't be caught.
                    tb = traceback.format_exc()
                    error_msg = "Error running bot.main:\n{error}".format(
                        error=bot.code_block(tb))
                    # Avoid adding duplicates.
                    if len(log_buffer) == 0 or log_buffer[-1] != error_msg:
                        log_buffer.append(error_msg)
                time.sleep(ERROR_TIMEOUT)
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
