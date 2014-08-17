"""Execute all CompileBot tests.

Run: python -m tests.all
(Note: Must be run from the compilebot directory)

"""
from runpy import run_module

def main():
    run_module('tests.unit')['main']()
    run_module('tests.integration')['main']()

if __name__ == "__main__":
    main()
