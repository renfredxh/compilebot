import time
import traceback
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
            except Exception as e:
                bot.log("Error running bot.main: {error}".format(
                        error=e), alert=True)
            bot.log("Round Finished. Sleeping for {time} 
                    "seconds".format(time=SLEEP_TIME))
            time.sleep(SLEEP_TIME)
    except KeyboardInterrupt:
        exit_msg = ''
    except Exception as e:
        tb = traceback.format_exc()
        exit_msg = "Depoyment error: {traceback}\n".format(traceback=tb)
    finally:
        bot.log("{msg}Bot shutting down".format(msg=exit_msg), alert=True)
        
if __name__ == "__main__":
    main()