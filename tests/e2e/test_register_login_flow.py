from seleniumbase import BaseCase
import uuid

class AuthTests(BaseCase):
    stored_username = None

    def test_01_register_user(self):
        # Visit the register page
        self.open("http://localhost:5000/register")

        username = f"selenium_{uuid.uuid4().hex[:8]}"
        AuthTests.stored_username = username

        # Fill the form
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', "Password123!")

        # Submit form
        self.click('button[type="submit"]')

        # Assert success message appears on the page
        self.assert_text("User registered successfully", "body")

    def test_02_login_success(self):
        self.open("http://localhost:5000/")

        username = AuthTests.stored_username

        # Log in using the same test user
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', "Password123!")

        self.click('button[type="submit"]')

        # Assert that login redirected to the movie page
        self.assert_text("Now Showing", "body")

    def test_03_login_invalid_password(self):
        self.open("http://localhost:5000/")

        username = AuthTests.stored_username

        self.type('input[name="username"]', username)
        self.type('input[name="password"]', "WrongPassword")

        self.click('button[type="submit"]')

        # Assert invalid password message
        self.assert_text("Invalid password", "body")

    def test_04_login_user_not_found(self):
        self.open("http://localhost:5000/")

        self.type('input[name="username"]', "ghost_user")
        self.type('input[name="password"]', "anything")

        self.click('button[type="submit"]')

        # Assert user does not exist message
        self.assert_text("User does not exist", "body")
