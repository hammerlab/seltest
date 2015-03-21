# Seltest

The simple, fast, visual testing framework for web applications.

```bash
pip install --upgrade seltest
```

Seltest automatically does what you would do manually. It checks all the pages
of your website after every change you make to the website to ensure nothing has
broken.

Because you're responsible and totally do that.

And yes, while testing individual components of your web application is well and
good, sometimes you don't have time for that. When it's one of those times, just
write a lines to test everything.

```python
class Website(seltest.Base):
  base_url = 'localhost:4000'
  def base(self, driver): pass
  def clicking_buttons(self, driver):
    driver.select_element_by_css_selector('#my-btn').click()
```

And test it with `sel test .`.

```
Testing images...
 for Website
  • website_base: no image found, creating initial screenshot
  • website_clicking-buttons: no image found, creating initial screenshot
```

Then, say I change a little something that happens when the button is clicked
and run `sel test .` again...

```
Testing images...
 for Website
  ✓ website_base: no change
  ✗ website_clicking-buttons: change detected, check the new image!
```

And that's just the beginning of what you can do. Try using this with your
continual integration server, or testing your entire website across all
browsers, automatically.

---


Seltest will connect to your test server on `localhost:4000` and take a
screenshot of the resulting page in Firefox (this is configurable with, say `-d
chrome`). If it's different from the last time it took that screenshot, it'll
let you know. Maybe the difference is what you expected. Maybe it's not. But now
you know. Like a magic crystal ball, seltest lets you know what's up.`

Seltest waits for the page to load, AJAX requests to complete, can wait for
specific elements or text to appear on the page. It can do anything a user
manually running the website on any browser could do, but it does it
automatically. That's good.


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

We could run the tests with `sel test tests/directory`, or get info about the
tests that would be run with, say, a class filter:
`selt list -vc runs tests/directory`.

I've found it useful to, when running in a version-controlled project, run
something like `sel update -d phantomjs -o tests/images tests`. My images, if
they're changed are overwritten, and then I use
[webdiff](https://github.com/danvk/webdiff) (`git webdiff`) to quickly show me
any differences between my previous images under version control and these newly
generated ones.

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


# Interactive Driving & Debugging Tests

If you'd like to play with seleniun and drive a browser, you can use `sel
interactive -d chrome`, for example. This opens a python shell (make sure you
have [IPython](http://ipython.org/) installed for a better experience!) with the
`driver` variable initialized to the selenium driver controlling the browser
that has just been opened for you.

Use it to explore the available API, and make sure the tests you're writing are
doing what you want them to do.

# Config

Seltest can use as defaults a config file in either `~/.seltestrc` or `./seltestrc`.

It must look like this (note that it looks just as the command line options
would appear: this makes it easy to remember & consult `sel --help`).

To see what configuration is being used for any particular invocation of `sel`,
use `sel <command> --list-config`.

Note: the `[arguments]` heading is required.

```
[arguments]
--firefox-path=~/somewhere/there/is/firefox-bin
-v
```

