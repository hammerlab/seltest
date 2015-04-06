from seltest import Base, url, hide


window_size = [200, 200]
base_url = 'google.com'

class GoogleTest(Base):
    def base(self, driver): pass

    def title(self, driver):
        assert driver.title == 'Google', 'title should be "Google"'

    def bad_title(self, driver):
        assert driver.title != 'Google', 'this assertion should fail!'

    @hide('center')
    def hidden(self, driver): pass
