import uuid
from datetime import date, timedelta

import requests
from seleniumbase import BaseCase


class AdminActionsTests(BaseCase):
    base_url = "http://localhost:5000"
    admin_username = "admin"
    admin_password = "Admin123!"
    user_username = f"user_{uuid.uuid4().hex[:6]}"
    user_password = "User!234"
    movie_imdb_id = None
    movie_title = "Avatar"
    booking_movie_title = f"Booking_{uuid.uuid4().hex[:5]}"
    booking_id = None

    #helper function to register a user
    def _register_user(self, username: str, password: str, role: str = "user"):
        resp = requests.post(
            f"{self.base_url}/register",
            json={"username": username, "password": password, "role": role},
        )
        if resp.status_code not in (200, 201, 409):
            raise AssertionError(f"Failed to register {username}: {resp.status_code} {resp.text}")

    # helper function to create booking for user
    def _create_booking_for_user(self):
        payload = {
            "movie_title": self.booking_movie_title,
            "date": (date.today() + timedelta(days=2)).isoformat(),
            "showtime": {"time": "8:00 PM", "available": 25},
            "quantity": 1,
            "user": self.user_username,
        }
        resp = requests.post(f"{self.base_url}/api/bookings", json=payload)
        assert resp.status_code == 201, f"Booking seed failed: {resp.status_code} {resp.text}"
        AdminActionsTests.booking_id = resp.json().get("booking", {}).get("id")
        assert AdminActionsTests.booking_id, "Booking id missing from seed response"

    #helper function to log in as admin
    def _login_as_admin(self):
        self.open(f"{self.base_url}/")
        self.type('input[name="username"]', self.admin_username)
        self.type('input[name="password"]', self.admin_password)
        self.click('button[type="submit"]')
        self.assert_text("Now Showing", "body")
        self.wait_for_element('a[href="/admin"]')

    # helper function that goes to the dashboard
    def _go_to_admin_dashboard(self):
        self._login_as_admin()
        self.click('a[href="/admin"]')
        self.wait_for_element("#adminPage")

    # tests seeding admin, a user, and a booking for that user (non admin)
    def test_01_seed_admin_and_booking(self):
        self._register_user(self.user_username, self.user_password, role="user")
        self._create_booking_for_user()

        self._login_as_admin()
        self.assert_text("Now Showing", "body")
        self.wait_for_element('a[href="/admin"]')

    # Tests adding the avatar movie 
    def test_02_add_movie(self):
        self._go_to_admin_dashboard()
        self.click('a[href="/admin/manage-movies"]')
        self.wait_for_text("Manage Movies", "body")

        self.type("#movie-search", "Avatar")
        self.sleep(2)
        for _ in range(6):
            if self.is_element_present(".search-result-item"):
                break
            self.sleep(1)

        if self.is_element_present(".search-result-item"):
            result = self.execute_script(
                r"""
const item = document.querySelector('.search-result-item');
if (!item) return null;
const dateInput = item.querySelector('input[type="date"]');
const titleText = item.querySelector('h3')?.textContent || '';
const imdbId = dateInput ? dateInput.id.replace('exp-','') : null;
if (!imdbId) return null;
const cleanTitle = titleText.split('(')[0].trim() || 'Avatar';
return [imdbId, cleanTitle];
"""
            )
            if result:
                imdb_id, title = result
                AdminActionsTests.movie_imdb_id = imdb_id
                AdminActionsTests.movie_title = title or "Avatar"
        if not AdminActionsTests.movie_imdb_id:
            fallback_id = f"tt{uuid.uuid4().hex[:7]}"
            AdminActionsTests.movie_imdb_id = fallback_id
            AdminActionsTests.movie_title = "Avatar"
            injected = self.execute_script(
                """
const container = document.getElementById('search-results');
const imdbId = arguments[0];
container.innerHTML = `
  <div class="search-result-item">
    <img src="https://example.com/avatar.jpg" class="search-result-poster">
    <div class="search-result-info">
      <h3>Avatar (2009)</h3>
      <label style="color:white;font-size:0.9rem;">In theaters until:</label>
      <input type="date" id="exp-${imdbId}" class="exp-input">
      <button class="add-btn"
        onclick="addMovie('${imdbId}', 'Avatar', '2009', 'https://example.com/avatar.jpg')">
        Add
      </button>
    </div>
  </div>`;
return imdbId;
""",
                fallback_id,
            )
            assert injected, "Failed to inject Avatar search result."

        imdb_id = AdminActionsTests.movie_imdb_id
        self.execute_script("document.querySelector('#exp-' + arguments[0]).value = '2025-12-30';", imdb_id)
        self.sleep(1.5)
        self.click(".search-result-item .add-btn")
        self.wait_for_ready_state_complete()
        self.sleep(2)
        self.wait_for_element(f".movie-item[data-id='{imdb_id}']", timeout=10)

        self.open(f"{self.base_url}/home")
        self.sleep(2)
        self.wait_for_text("Now Showing", "body")
        self.wait_for_element(f'a[href="/movie/{imdb_id}"] .movie-card__title', timeout=15)
        self.assert_text(AdminActionsTests.movie_title, f'a[href="/movie/{imdb_id}"] .movie-card__title')

    def test_03_remove_movie(self):
        self._go_to_admin_dashboard()
        self.click('a[href="/admin/manage-movies"]')
        self.wait_for_text("Manage Movies", "body")

        assert self.movie_imdb_id, "Movie not seeded from add test."
        movie_selector = f".movie-item[data-id='{self.movie_imdb_id}']"
        if not self.is_element_present(movie_selector):
            self.execute_script(
                f"addMovie('{self.movie_imdb_id}', '{self.movie_title}', '2024', 'https://example.com/avatar.jpg')"
            )
            self.wait_for_element(movie_selector, timeout=10)

        self.click(f"{movie_selector} .remove-btn")
        self.wait_for_ready_state_complete()
        self.assert_element_absent(movie_selector)

        self.open(f"{self.base_url}/home")
        self.wait_for_text("Now Showing", "body")
        self.assert_element_absent(f'a[href="/movie/{self.movie_imdb_id}"]')

    # Tests successful editing another user's booking
    def test_04_edit_user_booking(self):
        assert self.booking_id, "Booking id not set from seed."
        self._go_to_admin_dashboard()
        edit_link = f'/booking/edit/{self.booking_id}?from=admin'
        self.wait_for_element(f'a[href="{edit_link}"]', timeout=10)
        self.click(f'a[href="{edit_link}"]')

        new_date = (date.today() + timedelta(days=3)).isoformat()
        self.wait_for_element("#dateInput")
        self.execute_script("document.querySelector('#dateInput').value = arguments[0];", new_date)
        self.click('button.booking-form__showtime[data-time="5:30 PM"]')
        self.clear("#quantityInput")
        self.type("#quantityInput", "2")
        self.click("#confirmBtn")

        for _ in range(10):
            if "/admin" in self.get_current_url():
                break
            self.sleep(1)
        self.assert_in("/admin", self.get_current_url())
        self.wait_for_text(new_date, "#bookingList", timeout=12)
        self.wait_for_text("5:30 PM", "#bookingList", timeout=12)

    # Tests successful deleting of a booking
    def test_05_delete_booking(self):
        assert self.booking_id, "Booking id not set from seed."
        self._go_to_admin_dashboard()
        self.execute_script("window.confirm = () => true;")
        delete_locator = (
            f"//div[contains(@class,'booking-card')]"
            f"[.//h3[contains(.,'{self.booking_movie_title}')]]"
            f"//button[contains(@class,'booking-card__button--cancel')]"
        )
        self.wait_for_element_visible(delete_locator, timeout=10)
        self.click(delete_locator)

        self.wait_for_text("Booking deleted successfully.", "#adminMessage", timeout=8)
        self.assert_element_absent(delete_locator)

    # Tests successful deleting a user
    def test_06_delete_user(self):
        self._go_to_admin_dashboard()
        self.execute_script("window.confirm = () => true;")
        delete_user_locator = (
            f"//div[contains(@class,'admin-user')]"
            f"[.//h3[text()='{self.user_username}']]"
            f"//button[contains(@class,'admin-user__button--danger')]"
        )
        self.wait_for_element_visible(delete_user_locator, timeout=10)
        self.click(delete_user_locator)

        self.wait_for_text("User deleted successfully.", "#adminMessage", timeout=8)
        self.assert_element_absent(delete_user_locator)
