compilebot
==========

CompileBot is a reddit bot that can execute source code in comments. All you have to do is mention CompileBot in your comments along with a language and source code:

> +[/u/CompileBot](http://www.reddit.com/user/CompileBot) python
> 
>     print "Hello World!"
> 

CompileBot will then process your comment, execute it remotely, and then respond with the output:

> Output:
> 
>     Hello World!
>     

* You can view more information on how to use compilebot on the [compilebot wiki](http://www.reddit.com/r/CompileBot/wiki/index#wiki_how_to_use_compilebot). 
* [Try compilebot out on reddit](http://www.reddit.com/r/CompileBot/comments/1ueer5/official_compilebot_testing_thread/)

# How it works

CombileBot is powered by the "compilebot" module which is written in python (2.7). It uses the [PRAW](https://github.com/praw-dev/praw) package to communicate with reddit and a [modified fork](https://github.com/renfredxh/ideone-api) of the python [ideone-api](https://github.com/jschaf/ideone-api) which uses the [Ideone online compiler](http://ideone.com) to execute source code.

# Contributing

CompileBot would appreciate any help it can get. Even if you don't want to contribute to the compilebot source, we need people for testing, improving documentation, and making donations to help support CompileBot's server space and ideone subscription. For more details on with contributing with anything non-technical, you can find out more on the [CompileBot contribution wiki](http://www.reddit.com/r/CompileBot/wiki/index#wiki_contributing).

If you would like to contribute new features, or fix bugs or contribute anything else to the compilebot module, you can follow the instructions below to get a local instance of compilebot set up on your system.

# Installation

To install compilebot, you can follow the following steps. Using [virtualenv](http://www.virtualenv.org) is recommended.

```bash
git clone https://github.com/renfredxh/compilebot.git
cd compilebot
```

You'll need to initialize the ideone-api submodule and install it:

```bash
git submodule init
git submodule update
cd lib/ideone-api/
python setup.py install
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Now that all of the dependencies for compilebot have been installed, you'll have to configure the settings file. You can copy the included sample settings into a new file. From the main directory:

```bash
cd compilebot
cp sample-config.yml config.yml
```

Now, if you open `settings.json` in your favorite text editor you'll see customizable data for compilebot to use. If you would like to run all of compilebot's features, you'll need a [reddit](http://www.reddit.com/) account and a [ideone](http://ideone.com/account/register) account. Once you have your login credentials, you can edit `settings.json` and fill in the following fields:

```json
  "reddit_user": "<your reddit username>",
  "reddit_pass":  "<your reddit password>",
  "ideone_user": "<your ideone username>",
  "ideone_pass": "<your ideone password>",
```

Finally, try running compilebot:

```bash
python compilebot.py
```

# Testing

If you would like to test any changes, you can run the compilebot test suite in order to test each function. From the directory that contains compilebot.py, you can run all of the test modules:

```bash
python -m tests.run_all
```

The reply functions module tests a good amount of the compilebot functions and does not require any login requests. If you're only would like to run the reply functions:

```bash
python -m tests.test_reply
```

Disclaimer: the tests cases may not be perfect. The tests are written in a mostly white-box style and there is room for improvement. If you think a test is incorrect or would like to contribute improvements, please feel free to.
