import os
import uuid

from seleniumbase import BaseCase


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5000").rstrip("/")


class RegisterLoginFlowTests(BaseCase):
    #End-to-end coverage of the register and login flows. 

    def setUp(self):
        super().setUp()
        self.base_url = BASE_URL

    def _unique_credentials(self):
        suffix = uuid.uuid4().hex[:8]
        return f"selenium_user_{suffix}", "SeleniumTest123!"

    def _register_via_ui(self, username, password):
        self.open(f"{self.base_url}/register")
        self.wait_for_element_visible("#register-form", timeout=10)
        self.type("#register-form #username", username)
        self.type("#register-form #password", password)
        self.click("#register-form button.register-button")
        self.wait_for_text("User registered successfully", "#register-message", timeout=8)

    def _login_via_ui(self, username, password):
        self.open(f"{self.base_url}/")
        self.wait_for_element_visible("#landing-login-form", timeout=10)
        self.type("#landing-login-form input[name='username']", username)
        self.type("#landing-login-form input[name='password']", password)
        self.click("#landing-login-form button.login__button")
        self.wait_for_element("h1.movie-list__title", timeout=10)
        self.assert_true(self.get_current_url().endswith("/home"))

    def test_user_can_register(self):
        username, password = self._unique_credentials()
        self._register_via_ui(username, password)

    def test_user_can_login(self):
        username, password = self._unique_credentials()
        self._register_via_ui(username, password)
        self._login_via_ui(username, password)
