import re
import uuid
from datetime import date, timedelta

import requests
from seleniumbase import BaseCase


class BookingFlowTests(BaseCase):
    base_url = "http://localhost:5000"
    stored_username = None
    stored_password = "Password123!"
    movie_title = None

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

    def test_02_cancel_booking(self):
        username = BookingFlowTests.stored_username
        assert username, "Previous tests did not store a username."

        # Create a booking via HTTP before using Selenium
        session_client = requests.Session()
        login_resp = session_client.post(
            f"{self.base_url}/login",
            json={"username": username, "password": self.stored_password},
        )
        assert login_resp.ok, f"API login failed: {login_resp.status_code}, {login_resp.text}"

        movie_title = None
        home_resp = session_client.get(f"{self.base_url}/home")
        if home_resp.ok:
            match = re.search(r'<h3 class="movie-card__title">(.*?)</h3>', home_resp.text)
            if match:
                movie_title = match.group(1).strip()
        movie_title = movie_title or "Wicked: For Good"

        booking_date = (date.today() + timedelta(days=1)).isoformat()
        unique_showtime = f"Auto-{uuid.uuid4().hex[:6]}"
        payload = {
            "movie_title": movie_title,
            "date": booking_date,
            "showtime": {"time": unique_showtime, "available": 20},
            "quantity": 1,
            "user": username,
        }
        create_resp = session_client.post(f"{self.base_url}/api/bookings", json=payload)
        assert create_resp.status_code == 201, f"Booking creation failed: {create_resp.status_code}, {create_resp.text}"
        booking_id = create_resp.json().get("booking", {}).get("id")
        assert booking_id, "Booking ID missing from creation response."

        # Login via UI
        self.open(self.base_url + "/")
        self.type('input[name="username"]', username)
        self.type('input[name="password"]', self.stored_password)
        self.click('button[type="submit"]')
        self.assert_text("Now Showing", "body")

        # Go to bookings and cancel the one we just created
        self.open(self.base_url + "/my-bookings")
        card_selector = f'.booking-card[data-booking-id="{booking_id}"]'
        self.assert_element(card_selector)
        self.assert_text(movie_title, f"{card_selector} .booking-card__title")
        datetime_text = self.get_text(f"{card_selector} [data-booking-field='datetime']")
        self.assert_true(unique_showtime in datetime_text)
        self.click(f"{card_selector} .booking-card__button--cancel")
        self.assert_text("Booking cancelled successfully.", "#bookingsMessage")
        self.assert_element_absent(card_selector)
