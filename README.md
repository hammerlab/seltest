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
  sel list [options] <path>
  sel --version

Options:
  -h --help                      Show this screen.
  --version                      Show version.
  -f FILTER --filter FILTER      Only operate on tests matching regexp FILTER.
                                 Can be a comma-separated list of names.
  -c NAME --classname NAME       Only operate on test classes named NAME.
                                 Can be a comma-separated list of names.
```

# Example

Assuming we have the server we want to test at `localhost:5001`, we might write the below.

We could run the tests with `selt test /directory/containing/test/`.

```python
# test.py
# -*- coding: utf-8 -*-
from seltest import url, waitfor, Base

PORT = 5001
BASE = 'localhost:{}'.format(PORT)


class Website(Base):
    @url(BASE + '/about')
    def about_page(self, driver): pass

    @url(BASE + '/comments')
    def comments(self, driver): pass


class Runs(Base):
    @url(BASE)
    def runs_page(self, driver): pass

    @url(BASE)
    @waitfor('div.p#status', text='ready')
    def runs_info(self, driver):
        run = driver.find_element_by_css_selector('tr.run')
        run.click()

    @url(BASE)
    def runs_bams(self, driver):
        bam_btn_sel = 'div.project:last-child .project-stats a:first-child'
        bams = driver.find_element_by_css_selector(bam_btn_sel)
        bams.click()

````
