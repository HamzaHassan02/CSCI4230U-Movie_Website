import uuid
from seleniumbase import BaseCase


class BookingFlowTests(BaseCase):
    base_url = "http://localhost:5000"
    stored_username = None
    stored_password = "Password123!"
    movie_title = "Interstellar"

    def test_01_register_and_login(self):
        username = f"booking_{uuid.uuid4().hex[:8]}"
        BookingFlowTests.stored_username = username

        # Register
        self.open(f"{self.base_url}/register")
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', self.stored_password)
        self.click('button[type="submit"]')
        self.assert_text("User registered successfully", "#register-message")

        # Login
        self.open(self.base_url + "/")
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', self.stored_password)
        self.click('button[type="submit"]')
        self.assert_text("Now Showing", "body")

    def test_02_create_booking(self):
        username = BookingFlowTests.stored_username
        assert username, "Previous test did not store a username."

        # Login 
        self.open(self.base_url + "/")
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', self.stored_password)
        self.click('button[type="submit"]')
        self.assert_text("Now Showing", "body")

        # Navigate to movie detail
        self.click('//a[contains(@class,"movie-card")][.//h3[contains(.,"Interstellar")]]')
        self.assert_text(self.movie_title, "body")

        # Go to booking screen
        self.click('//button[contains(@class,"movie-details__button") and contains(text(),"Book Now")]')
        self.assert_text("Booking", "body")

        # Fill booking form
        self.set_value("#dateInput", "2025-04-01")
        self.click("body")
        self.click(".booking-form__showtime")
        self.type("#quantityInput", "2")
        self.click("#confirmBtn")

        # Verify success
        self.assert_text("Booking saved successfully!", "#bookingMessage")

        # View bookings page
        self.open(self.base_url + "/my-bookings")
        self.assert_text(self.movie_title, ".booking-card__title")
        self.assert_text("Seats: 2", '[data-booking-field="quantity"]')

    def test_03_update_booking(self):
        username = BookingFlowTests.stored_username
        assert username, "Previous tests did not store a username."

        # Login
        self.open(self.base_url + "/")
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', self.stored_password)
        self.click('button[type="submit"]')
        self.assert_text("Now Showing", "body")

        # Open bookings and go to edit page
        self.open(self.base_url + "/my-bookings")
        self.click(".booking-card__button--edit")
        self.assert_text("Update Booking", "#confirmBtn")

        # Update booking fields
        self.set_value("#dateInput", "2025-04-02")
        self.click("body")
        self.click(".booking-form__showtime:nth-of-type(2)")
        self.update_text("#quantityInput", "3")
        self.click("#confirmBtn")

        # Wait for update confirmation and redirect
        self.wait_for_text("Booking updated successfully!", "#bookingMessage", timeout=10)
        self.assert_url_contains("/my-bookings")

        # Verify updated details
        self.assert_text("2025-04-02", '[data-booking-field="datetime"]')
        self.assert_text("5:30 PM", '[data-booking-field="datetime"]')
        self.assert_text("Seats: 3", '[data-booking-field="quantity"]')

    def test_04_cancel_booking(self):
        username = BookingFlowTests.stored_username
        assert username, "Previous tests did not store a username."

        # Login
        self.open(self.base_url + "/")
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', self.stored_password)
        self.click('button[type="submit"]')
        self.assert_text("Now Showing", "body")

        # Go to bookings and cancel
        self.open(self.base_url + "/my-bookings")
        self.click(".booking-card__button--cancel")
        self.assert_text("Booking cancelled successfully.", "#bookingsMessage")
        self.assert_element_absent(".booking-card")
