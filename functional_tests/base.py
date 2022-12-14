import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings

from .server_tools import reset_database, create_session_on_server
from .management.commands.create_session import create_pre_authenticated_session


MAX_WAIT = 20  # dont forget to change back to 20
WAIT_TIME = 0.1
SCREEN_DUMP_LOCATION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'screendumps'
)


def wait(fn):
    def modified_fn(*args, **kwargs):
        start_time = time.time()
        while True:
            try:
                return fn(*args, **kwargs)
            except (AssertionError, WebDriverException) as e:
                if time.time() - start_time > MAX_WAIT:
                    raise e
                time.sleep(WAIT_TIME)
    return modified_fn


class FunctionalTest(StaticLiveServerTestCase):
    def setUp(self) -> None:
        self.browser = webdriver.Firefox()

        self.staging_server = os.environ.get('STAGING_SERVER')
        if self.staging_server:
            self.live_server_url = 'http://' + self.staging_server
            reset_database(self.staging_server)

    def tearDown(self) -> None:
        if self._test_has_failed():
            if not os.path.exists(SCREEN_DUMP_LOCATION):
                os.makedirs(SCREEN_DUMP_LOCATION)
            for ix, handle in enumerate(self.browser.window_handles):
                self._windowid = ix
                self.browser.switch_to.window(handle)
                self.take_screenshot()
                self.dump_html()
        self.browser.quit()
        super().tearDown()

    def _test_has_failed(self):
        return any(error for (method, error) in self._outcome.errors)

    def take_screenshot(self):
        filename = self._get_filename() + '.png'
        print('screenshotting to', filename)
        self.browser.get_screenshot_as_file(filename)

    def dump_html(self):
        filename = self._get_filename() + '.html'
        print('dumping page HTML to', filename)
        with open(filename, 'w') as f:
            f.write(self.browser.page_source)

    def _get_filename(self):
        timestamp = datetime.now().isoformat().replace(':', '.')[:19]
        return f'{SCREEN_DUMP_LOCATION}/' \
               f'{self.__class__.__name__}.{self._testMethodName}-window{self._windowid}-{timestamp}'

    def create_pre_authenticated_session(self, email):
        if self.staging_server:
            session_key = create_session_on_server(self.staging_server, email)
        else:
            session_key = create_pre_authenticated_session(email)

        ## To set a cookie we need to first visit the domain.
        ## 404 page loads the quickest!
        self.browser.get(self.live_server_url+'/404_no_such_url/')
        self.browser.add_cookie({
            'name': settings.SESSION_COOKIE_NAME,
            'value': session_key,
            'path': '/'
        })

    def get_table_rows(self):
        return self.browser.find_elements(by=By.CSS_SELECTOR, value='#id_list_table tr')

    @wait
    def wait_for_row_in_list_table(self, item_text, item_number):
        expected_row_text = f'{item_number}: {item_text}'
        rows = self.get_table_rows()
        self.assertIn(expected_row_text, [row.text for row in rows])

    def get_item_input_box(self):
        return self.browser.find_element(by=By.ID, value='id_text')

    def add_list_item(self, item_text):
        new_item_no = len(self.get_table_rows()) + 1
        self.get_item_input_box().send_keys(item_text)
        self.get_item_input_box().send_keys(Keys.ENTER)
        self.wait_for_row_in_list_table(item_text, new_item_no)
        return self

    @wait
    def wait_for(self, fn):
        return fn()

    @wait
    def wait_for_login(self, email):
        self.browser.find_element(by=By.LINK_TEXT, value='Log out')
        navbar = self.browser.find_element(by=By.CSS_SELECTOR, value='.navbar')
        self.assertIn(email, navbar.text)

    @wait
    def wait_for_logout(self, email):
        self.browser.find_element(by=By.NAME, value='email')
        navbar = self.browser.find_element(by=By.CSS_SELECTOR, value='.navbar')
        self.assertNotIn(email, navbar.text)
