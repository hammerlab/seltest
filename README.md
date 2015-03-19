# Seltest

A simple, fast, perceptual diff testing framework for web applications.

Waits for AJAX requests to complete, or can wait for certain elements
explicitly, and compares screenshots of the app rendered in Chrome.

(Currently only works with Chrome, will be adding Safari and FireFox support
soon)


# Install

```
brew install chromedriver  # or `pip install chromedriver` if on Windows or Linux
pip install seltest
```


# Usage

```
Seltest, the saltiest tests.

Usage:
  sel test [options] <path>
  sel update [options] <path>
  sel list [options] <path>
  sel interactive [options]
  sel --version

Options:
  -h --help                      Show this screen.
  --version                      Show version.
  -v                             Verbose mode.
  -f FILTER --filter FILTER      Only operate on tests matching regexp FILTER.
                                 Can be a comma-separated list of names.
  -c NAME --classname NAME       Only operate on test classes named NAME.
                                 Can be a comma-separated list of names.
  -d NAME --driver NAME          Driver/Browser to run with. Can be one of
                                 chrome, firefox. Defaults to firefox.
  --firefox-path                 Path to Firefox binary, if you don't want to
                                 use the default.
  -o PATH --output PATH          Path where images will be saved; default is <path>.
  --config                       Path to config file. Default is to first look
                                 at ./.seltestrc, and then ~/.seltestrc
  --list-config                  Print out the current configuration being used.
  --wait SECONDS                 Wait SECONDS between each test. Useful for
                                 debugging tests and manually monitoring them.
                                 Defaults to 0.
```

# Example

Assuming we have the server we want to test at `localhost:5001`, we might write the below.

We could run the tests with `selt test tests/directory`, or get info about the
tests that would be run with, say, a class filter:
`selt list -vc runs tests/directory`.

```python
# test.py
# -*- coding: utf-8 -*-
from seltest import url, waitfor, Base

BASE = 'localhost:5000'

class Website(Base):
    base_url = BASE

    @url('/about')
    def about_page(self, driver): pass

    @url('/comments')
    def comments(self, driver): pass


class Runs(Base):
    base_url = BASE

    def page(self, driver):
        """Shows the default runs page."""
        pass

    @waitfor('div.p#status', text='ready')
    def info(self, driver):
        run = driver.find_element_by_css_selector('tr.run')
        run.click()

    def bams(self, driver):
        bam_btn_sel = 'div.project:last-child .project-stats a:first-child'
        bams = driver.find_element_by_css_selector(bam_btn_sel)
        bams.click()

````

# Config

Seltest can use as defaults a config file in either `~/.seltestrc` or `./seltestrc`.

It must look like this (note that it looks just as the command line options
would appear: this makes it easy to remember & consult `sel --help`).

Note: the `[arguments]` heading is required.

```
[arguments]
--firefox-path=~/somewhere/there/is/firefox-bin
-v
```

