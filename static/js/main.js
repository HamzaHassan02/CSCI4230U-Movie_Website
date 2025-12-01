const safeParseJSON = (value) => {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch (error) {
    console.warn('Failed to parse JSON:', error);
    return null;
  }
};

const initAdminPage = () => {
  const adminRoot = document.getElementById('adminPage');
  if (!adminRoot) return;

  const adminMessage = document.getElementById('adminMessage');
  const userList = document.getElementById('userList');
  const bookingList = document.getElementById('bookingList');
  const userCount = document.getElementById('userCount');
  const bookingCount = document.getElementById('bookingCount');
  const currentUsername = adminRoot.dataset.currentUsername || '';

  const setMessage = (text) => {
    if (adminMessage) {
      adminMessage.textContent = text || '';
    }
  };

  const clearAndSetEmpty = (container) => {
    if (!container) return;
    container.innerHTML = '';
    const empty = document.createElement('p');
    empty.className = 'admin-list__empty';
    empty.textContent = container.dataset.emptyText || 'Nothing to show yet.';
    container.appendChild(empty);
  };

  const deleteBooking = async (bookingId, cardEl) => {
    if (!bookingId) return;
    const btn = cardEl?.querySelector('.booking-card__button--cancel');
    const originalText = btn?.textContent;
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Deleting...';
    }
    try {
      const response = await fetch(`/api/bookings/${bookingId}`, { method: 'DELETE' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || 'Failed to delete booking.');
      }
      cardEl?.remove();
      const remaining = bookingList?.querySelectorAll('.booking-card').length ?? 0;
      if (bookingCount) bookingCount.textContent = remaining;
      if (remaining === 0) {
        clearAndSetEmpty(bookingList);
      }
      setMessage('Booking deleted successfully.');
    } catch (error) {
      console.error('Failed to delete booking', error);
      setMessage(error.message || 'Unable to delete booking.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = originalText || 'Delete Booking';
      }
    }
  };

  const deleteUser = async (userId, cardEl) => {
    if (!userId) return;
    const btn = cardEl?.querySelector('.admin-user__button--danger');
    const originalText = btn?.textContent;
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Deleting...';
    }
    try {
      const response = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || 'Failed to delete user.');
      }
      cardEl?.remove();
      const remaining = userList?.querySelectorAll('.admin-user').length ?? 0;
      if (userCount) userCount.textContent = remaining;
      if (remaining === 0) {
        clearAndSetEmpty(userList);
      }
      setMessage('User deleted successfully.');
      await fetchBookings();
    } catch (error) {
      console.error('Failed to delete user', error);
      setMessage(error.message || 'Unable to delete user.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = originalText || 'Delete User';
      }
    }
  };

  const createUserCard = (user) => {
    const card = document.createElement('div');
    card.className = 'admin-user';

    const header = document.createElement('div');
    header.className = 'admin-user__header';

    const name = document.createElement('h3');
    name.className = 'admin-user__name';
    name.textContent = user.username || 'Unknown user';

    const role = document.createElement('span');
    role.className = 'admin-user__role';
    role.textContent = user.role || 'user';

    header.appendChild(name);
    header.appendChild(role);

    const meta = document.createElement('p');
    meta.className = 'admin-user__meta';
    meta.textContent = `ID: ${user.id ?? '—'}`;

    const actions = document.createElement('div');
    actions.className = 'admin-user__actions';

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'admin-user__button admin-user__button--danger';
    deleteBtn.textContent = 'Delete User';
    if (currentUsername && user.username === currentUsername) {
      deleteBtn.disabled = true;
      deleteBtn.textContent = 'Cannot delete self';
      deleteBtn.title = 'Admins cannot delete their own account.';
    } else {
      deleteBtn.addEventListener('click', async () => {
        if (!user.id) return;
        const confirmDelete = window.confirm(`Delete user "${user.username}"?`);
        if (!confirmDelete) return;
        await deleteUser(user.id, card);
      });
    }

    actions.appendChild(deleteBtn);

    card.appendChild(header);
    card.appendChild(meta);
    card.appendChild(actions);
    return card;
  };

  const createBookingCard = (booking) => {
    const card = document.createElement('div');
    card.className = 'booking-card booking-card--compact';

    const title = document.createElement('h3');
    title.className = 'booking-card__title';
    title.textContent = booking.movie_title || 'Unknown movie';

    const datetime = document.createElement('p');
    datetime.className = 'booking-card__info';
    datetime.textContent = `${booking.date || '—'} — ${booking.showtime || '—'}`;

    const quantity = document.createElement('p');
    quantity.className = 'booking-card__info';
    quantity.textContent = `Seats: ${booking.quantity ?? '—'}`;

    const user = document.createElement('p');
    user.className = 'booking-card__info booking-card__info--user';
    user.textContent = `Booked by: ${booking.user || 'Unknown'}`;

    const createdAt = document.createElement('p');
    createdAt.className = 'booking-card__info booking-card__info--meta';
    createdAt.textContent = booking.created_at
      ? `Created: ${new Date(booking.created_at).toLocaleString()}`
      : 'Created: —';

    const actions = document.createElement('div');
    actions.className = 'booking-card__actions booking-card__actions--admin';

    const editLink = document.createElement('a');
    editLink.className = 'booking-card__button booking-card__button--edit';
    editLink.textContent = 'Edit Booking';
    editLink.href = `/booking/edit/${booking.id}?from=admin`;

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'booking-card__button booking-card__button--cancel';
    deleteBtn.textContent = 'Delete Booking';
    deleteBtn.addEventListener('click', async () => {
      if (!booking.id) return;
      const confirmed = window.confirm(`Delete booking #${booking.id}?`);
      if (!confirmed) return;
      await deleteBooking(booking.id, card);
    });

    actions.appendChild(editLink);
    actions.appendChild(deleteBtn);

    card.appendChild(title);
    card.appendChild(datetime);
    card.appendChild(quantity);
    card.appendChild(user);
    card.appendChild(createdAt);
    card.appendChild(actions);
    return card;
  };

  const renderList = (container, items, createFn) => {
    if (!container) return;
    container.innerHTML = '';

    if (!items || items.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'admin-list__empty';
      empty.textContent = container.dataset.emptyText || 'Nothing to show yet.';
      container.appendChild(empty);
      return;
    }

    items.forEach((item) => container.appendChild(createFn(item)));
  };

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/users');
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || 'Failed to load users.');
      }

      const users = data.users || [];
      if (userCount) {
        userCount.textContent = users.length;
      }
      renderList(userList, users, createUserCard);
    } catch (error) {
      console.error('Failed to load users', error);
      setMessage(error.message || 'Unable to load users.');
      if (userCount) {
        userCount.textContent = '0';
      }
      clearAndSetEmpty(userList);
    }
  };

  const fetchBookings = async () => {
    try {
      const response = await fetch('/api/bookings');
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || 'Failed to load bookings.');
      }

      const bookings = data.bookings || [];
      if (bookingCount) {
        bookingCount.textContent = bookings.length;
      }
      renderList(bookingList, bookings, createBookingCard);
    } catch (error) {
      console.error('Failed to load bookings', error);
      setMessage(error.message || 'Unable to load bookings.');
      if (bookingCount) {
        bookingCount.textContent = '0';
      }
      clearAndSetEmpty(bookingList);
    }
  };

  fetchUsers();
  fetchBookings();
};

const initBookingsPage = () => {
  const bookingListEl = document.getElementById('bookingList');
  if (!bookingListEl) return;

  const bookingsMessage = document.getElementById('bookingsMessage');
  const currentUsername = bookingListEl.dataset.username || '';

  const setBookingsMessage = (text, timeoutMs = 0) => {
    if (!bookingsMessage) return;
    bookingsMessage.textContent = text || '';
    if (timeoutMs > 0 && text) {
      setTimeout(() => {
        if (bookingsMessage.textContent === text) {
          bookingsMessage.textContent = '';
        }
      }, timeoutMs);
    }
  };

  document.querySelectorAll('.booking-card__button--cancel').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const bookingId = btn.dataset.bookingId;
      if (!bookingId) {
        setBookingsMessage('Unable to determine booking id.');
        return;
      }

      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Cancelling...';

      try {
        const response = await fetch(`/api/bookings/${bookingId}`, {
          method: 'DELETE'
        });
        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
          btn.disabled = false;
          btn.textContent = originalText;
          setBookingsMessage(result.message || 'Failed to cancel booking.');
          return;
        }

        const bookingCard = btn.closest('.booking-card');
        if (bookingCard) {
          bookingCard.remove();
        }
        setBookingsMessage('Booking cancelled successfully.', 4000);

        if (bookingListEl && !bookingListEl.querySelector('.booking-card')) {
          const emptyEl = document.createElement('p');
          emptyEl.className = 'booking-card__empty';
          emptyEl.textContent = bookingListEl.dataset.emptyMessage || `No bookings found for ${currentUsername || 'this account'}.`;
          bookingListEl.appendChild(emptyEl);
        }
      } catch (error) {
        console.error('Failed to cancel booking', error);
        btn.disabled = false;
        btn.textContent = originalText;
        setBookingsMessage('Unexpected error while cancelling booking.');
      }
    });
  });
};

const initBookingForm = () => {
  const confirmBtn = document.getElementById('confirmBtn');
  const bookingDataEl = document.getElementById('bookingData');
  if (!confirmBtn || !bookingDataEl) return;

  const dateInput = document.getElementById('dateInput');
  const quantityInput = document.getElementById('quantityInput');
  const messageEl = document.getElementById('bookingMessage');

  const currentUser = bookingDataEl.dataset.currentUser || '';
  const existingBooking = safeParseJSON(bookingDataEl.dataset.existingBooking) || null;
  const movieTitle = bookingDataEl.dataset.movieTitle || '';
  const isEditMode = Boolean(existingBooking && existingBooking.id);

  let selectedShowtime = null;

  document.querySelectorAll('.booking-form__showtime').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedShowtime = {
        time: btn.dataset.time,
        available: Number(btn.dataset.available)
      };

      document.querySelectorAll('.booking-form__showtime').forEach(b => {
        b.classList.remove('selected-showtime');
      });

      btn.classList.add('selected-showtime');
    });
  });

  if (isEditMode) {
    confirmBtn.textContent = 'Update Booking';
    if (existingBooking.show_date) {
      dateInput.value = existingBooking.show_date;
    }
    if (existingBooking.quantity) {
      quantityInput.value = existingBooking.quantity;
    }
    if (existingBooking.showtime) {
      const matchingBtn = Array.from(document.querySelectorAll('.booking-form__showtime')).find(btn => btn.dataset.time === existingBooking.showtime);
      if (matchingBtn) {
        matchingBtn.classList.add('selected-showtime');
        selectedShowtime = {
          time: matchingBtn.dataset.time,
          available: Number(matchingBtn.dataset.available)
        };
      } else {
        selectedShowtime = {
          time: existingBooking.showtime,
          available: null
        };
      }
    }
  }

  confirmBtn.addEventListener('click', async () => {
    const date = dateInput.value;
    const quantityValue = quantityInput.value;
    const quantity = Number(quantityValue);
    messageEl.textContent = '';

    if (!currentUser) {
      messageEl.textContent = 'Unable to determine current user. Please log in again.';
      return;
    }

    if (!date) {
      messageEl.textContent = 'Please select a date before booking.';
      return;
    }

    if (!selectedShowtime) {
      messageEl.textContent = 'Please choose a showtime.';
      return;
    }

    if (!quantity || quantity <= 0) {
      messageEl.textContent = 'Please enter a valid quantity.';
      return;
    }

    const payload = {
      date,
      showtime: selectedShowtime,
      quantity
    };

    const isCreateMode = !isEditMode;
    const url = isCreateMode ? '/api/bookings/checkout' : `/api/bookings/${existingBooking.id}`;
    const method = isCreateMode ? 'POST' : 'PUT';

    if (isCreateMode) {
      payload.movie_title = movieTitle;
      payload.user = currentUser;
    }

    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (!response.ok) {
        const errorMsg = Array.isArray(result.errors) ? result.errors.join(', ') : result.message;
        messageEl.textContent = `Booking failed: ${errorMsg}`;
        return;
      }

      if (isCreateMode) {
        if (!result.checkout_url) {
          messageEl.textContent = 'Unable to start checkout. Please try again.';
          return;
        }
        messageEl.textContent = 'Redirecting to payment...';
        window.location.href = result.checkout_url;
        return;
      }

      messageEl.textContent = 'Booking updated successfully!';
      setTimeout(() => {
        const params = new URLSearchParams(window.location.search);
        const returnToAdmin = params.get('from') === 'admin';
        window.location.href = returnToAdmin ? '/admin' : '/my-bookings';
      }, 150);
    } catch (error) {
      console.error('Failed to save booking', error);
      messageEl.textContent = 'Unexpected error while saving booking. Please try again.';
    }
  });
};

document.addEventListener('DOMContentLoaded', () => {
  initAdminPage();
  initBookingsPage();
  initBookingForm();
});
