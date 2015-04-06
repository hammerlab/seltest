# API

The primary classes and functions exported by seltest are: `Base`, `url`,
`waitfor`, `dontwaitfor`, and `hide`.

All test classes must inherit from `Base`. All test methods within `Base` have
signature `(self, driver)`.

At the module and class level, the following attributes may be defined
(class-level attributes overriding the module-level attributes).

* `base_url`
  - (`str`) the URL relative to which all tests will be run. No `http://` required.
* `window_size`
  - (`[WIDTH, HEIGHT]`) sets the window size of the browser.

At the class level, you may set the following.

* `wait_for`
  - (`{"css_selector": SELECTOR_STRING, "classes": [CLASSNAME1, ..], "text":
    TEXT}`) before the screenshot is taken, seltest will wait for the conditions
    in `wait_for` to be satisfied.
    - `css_selector` is a typical CSS rule to select an element, e.g. `".classname
      div.anotherclass .etc"`
    - `classes`, optional is a list of classes we wait for the element to have.
    - `text`, optional, is the text we wait for the element to have.
  - You can set `wait_fors = [{..}]` instead, for a list of elements (and
    class/text conditions to wait for)

Decorators to be used on test methods are the following.

* `@url(URL_STRING)`
  - The URL the test should be run at, relative to the `base_url`, if any.
* `@waitfor(css_selector, text=None, classes=None)`
  - Elements to wait for (see `wait_for` above) on this particular test before
    taking the screenshot.
  - You can add as many of these to a single test as you'd like.
* `@dontwaitfor(css_selector)`
  - If there is a class-level `wait_for` or `wait_fors`, ignore it for this test.
* `@hid(css_selector)`
  - Removes all elements matching `css_selector` before the screenshot is taken.
  - You can add as many of these to a single test as you'd like.


# Examples

This example comes from a real use of seltest.

```python
# -*- coding: utf-8 -*-
from seltest import url, waitfor, dontwaitfor, hide, Base
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains


base_url = 'localhost:5001'
window_size = [1280, 800]

class Website(Base):
    @url('/about')
    def about_page(self, driver):
        """The about/API documentation page."""
        pass

    @url('/comments')
    @hide('span.time')
    def comments(self, driver):
        """Initial view of the comments page."""
        pass


class Runs(Base):
    def page(self, driver):
        """Initial view of the runs page."""
        pass

    def info(self, driver):
        """Showing an expanded run row and information."""
        run = driver.find_element_by_css_selector('tr.run')
        run.click()

    def bams(self, driver):
        """Showing the list of BAMs in a project."""
        bam_btn_sel = 'div.project:last-child .project-stats a:first-child'
        bams = driver.find_element_by_css_selector(bam_btn_sel)
        bams.click()


class Examine(Base):
    base_url = base_url + '/runs/1/examine'
    wait_for = {'css_selector': '.query-status', 'classes': ['good']}

    def base(self, driver):
        """Initial view of a fully-loaded Examine page."""
        pass

    @waitfor('tr:first-child td:nth-child(20)', text='0')
    def sorted(self, driver):
        """Examine page sorted by decreasing Normal Read Depth."""
        rd = driver.find_element_by_css_selector('[data-attribute="sample:RD"] a')
        rd.click()

    def tooltip(self, driver):
        """Examine page showing a Normal Read Depth tooltip."""
        dp = driver.find_element_by_css_selector('[data-attribute="sample:RD"]')
        ActionChains(driver).move_to_element(dp).perform()

    @url('?query=sample_name+%3D+NORMAL+AND+info%3ADP+%3E+50+ORDER+BY+info%3ADP%2C+sample%3ARD+DESC')
    def filter(self, driver):
        """Examine page showing a filtered view."""
        pass

    def comments_view(self, driver):
        """Examine page showing a comment in view mode."""
        row = driver.find_element_by_css_selector('tbody tr')
        row.click()

    def comments_edit(self, driver):
        """Examine page showing a comment in edit mode."""
        row = driver.find_element_by_css_selector('tbody tr')
        row.click()
        btn = driver.find_elements_by_css_selector('.comment-edit')[1]
        btn.click()

    @dontwaitfor('.query-status')
    @waitfor('.query-status', classes=['bad'])
    def bad_query(self, driver):
        """Examine page showing a poorly formed query."""
        input = driver.find_element_by_css_selector('input[type="text"].tt-input')
        input.send_keys('bad query is so bad')

    @waitfor('tr:nth-child(12) td:nth-child(2)', text=u'✓')
    def validation(self, driver):
        """Examine page with a validation."""
        select = Select(driver.find_element_by_tag_name('select'))
        select.select_by_visible_text('file:///tmp/truthy-snv.vcf')
```
