from flask import Blueprint, jsonify, request, session

from models import Booking, db

booking_bp = Blueprint("booking_api", __name__)


@booking_bp.route("/api/bookings", methods=["POST"])
def post_booking():
    #add a booking to the database
    payload = request.get_json() or {}
    movie_title = payload.get("movie_title")
    show_date = payload.get("date") or payload.get("data")
    showtime_payload = payload.get("showtime") or {}
    showtime_time = showtime_payload.get("time")
    showtime_available_raw = showtime_payload.get("available")
    quantity_raw = payload.get("quantity")
    booked_by = payload.get("user") or payload.get("username") or session.get("username")

    errors = []
    if not movie_title:
        errors.append("movie_title is required.")
    if not show_date:
        errors.append("date is required.")
    if not showtime_time:
        errors.append("showtime.time is required.")
    if not booked_by:
        errors.append("user is required.")

    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        quantity = None
        errors.append("quantity must be a positive integer.")

    showtime_available = None
    if showtime_available_raw is not None:
        try:
            showtime_available = int(showtime_available_raw)
        except (TypeError, ValueError):
            errors.append("showtime.available must be an integer.")

    if errors:
        return jsonify({"message": "Invalid booking payload", "errors": errors}), 400

    booking = Booking(
        movie_title=movie_title,
        show_date=show_date,
        showtime=showtime_time,
        showtime_available=showtime_available,
        quantity=quantity,
        booked_by=booked_by,
    )

    try:
        db.session.add(booking)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"message": "Failed to save booking", "error": str(exc)}), 500

    return (
        jsonify(
            {
                "message": "Booking stored successfully",
                "booking": {
                    "id": booking.id,
                    "movie_title": booking.movie_title,
                    "date": booking.show_date,
                    "showtime": {
                        "time": booking.showtime,
                        "available": booking.showtime_available,
                    },
                    "quantity": booking.quantity,
                    "user": booking.booked_by,
                },
            }
        ),
        201,
    )


@booking_bp.route("/api/bookings/<int:booking_id>", methods=["PATCH"])
def update_booking(booking_id: int):
    # Update fields on a booking owned by the current user
    username = session.get("username")
    if not username:
        return jsonify({"message": "Authentication required"}), 401

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"message": "Booking not found"}), 404
    if booking.booked_by != username:
        return jsonify({"message": "Not authorized to update this booking"}), 403

    payload = request.get_json() or {}
    updates = {}
    if "date" in payload:
        new_date = payload.get("date")
        if not new_date:
            return jsonify({"message": "date cannot be empty"}), 400
        updates["show_date"] = new_date
    if "showtime" in payload:
        showtime_payload = payload.get("showtime") or {}
        new_time = showtime_payload.get("time")
        if not new_time:
            return jsonify({"message": "showtime.time cannot be empty"}), 400
        updates["showtime"] = new_time
        if "available" in showtime_payload and showtime_payload.get("available") is not None:
            try:
                updates["showtime_available"] = int(showtime_payload.get("available"))
            except (TypeError, ValueError):
                return jsonify({"message": "showtime.available must be an integer"}), 400
    if "quantity" in payload:
        try:
            new_quantity = int(payload.get("quantity"))
            if new_quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"message": "quantity must be a positive integer"}), 400
        updates["quantity"] = new_quantity

    if not updates:
        return jsonify({"message": "No valid fields provided for update"}), 400

    for field, value in updates.items():
        setattr(booking, field, value)

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"message": "Failed to update booking", "error": str(exc)}), 500

    return jsonify(
        {
            "message": "Booking updated successfully",
            "booking": {
                "id": booking.id,
                "movie_title": booking.movie_title,
                "date": booking.show_date,
                "showtime": {
                    "time": booking.showtime,
                    "available": booking.showtime_available,
                },
                "quantity": booking.quantity,
                "user": booking.booked_by,
            },
        }
    )


@booking_bp.route("/api/bookings/<int:booking_id>", methods=["DELETE"])
def delete_booking(booking_id: int):
    # Delete a booking owned by the current session user
    username = session.get("username")
    if not username:
        return jsonify({"message": "Authentication required"}), 401

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"message": "Booking not found"}), 404
    if booking.booked_by != username:
        return jsonify({"message": "Not authorized to cancel this booking"}), 403

    try:
        db.session.delete(booking)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"message": "Failed to delete booking", "error": str(exc)}), 500

    return jsonify({"message": "Booking cancelled successfully", "booking_id": booking_id})
