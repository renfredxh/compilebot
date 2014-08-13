import time
import traceback
from requests import HTTPError, ConnectionError
import compilebot as bot

SLEEP_TIME = 60

def main():
    try:
        bot.log("Initializing bot")
        while True:
            try:
                bot.main()
            except HTTPError as e:
                # HTTP Errors may indicate reddit is overloaded.
                # Sleep for some extra time. 
                bot.log(str(e) + " ")
                time.sleep(SLEEP_TIME*2)
            except ConnectionError as e:
                bot.log(str(e) + " ")
                time.sleep(SLEEP_TIME*2)
            except Exception as e:
                bot.log("Error running bot.main: {error}".format(
                        error=e), alert=True)
            time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        exit_msg = ''
    except Exception as e:
        tb = traceback.format_exc()
        exit_msg = "Depoyment error: {traceback}\n".format(traceback=tb)
        bot.log("{msg}Bot shutting down".format(msg=exit_msg), alert=True)
        
if __name__ == "__main__":
    main()
