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
  sel interactive (chrome | firefox)
  sel --version

Options:
  -h --help                      Show this screen.
  --version                      Show version.
  -v                             Verbose mode.
  -f FILTER --filter FILTER      Only operate on tests matching regexp FILTER.
                                 Can be a comma-separated list of names.
  -c NAME --classname NAME       Only operate on test classes named NAME.
                                 Can be a comma-separated list of names.
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
