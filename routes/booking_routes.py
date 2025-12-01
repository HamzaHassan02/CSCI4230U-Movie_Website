import os

import stripe
from flask import Blueprint, jsonify, render_template, request, session, url_for
from datetime import datetime, date
from models import Booking, Movie, db

booking_bp = Blueprint("booking_api", __name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
try:
    TICKET_PRICE_CENTS = int(os.getenv("TICKET_PRICE_CENTS", "1500"))
except ValueError:
    TICKET_PRICE_CENTS = 1500


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
    
    movie = Movie.query.filter_by(title=movie_title).first()
    if movie and movie.expiration:
        today = date.today()
        booking_date_obj = datetime.strptime(show_date, "%Y-%m-%d").date()
        # Cannot book before today
        if booking_date_obj < today:
            return jsonify({"message": "You cannot book a date in the past."}), 400
        # Cannot book after expiration
        if booking_date_obj > movie.expiration:
            return jsonify({
                "message": f"This movie is no longer in theaters after {movie.expiration}."
            }), 400

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


@booking_bp.route("/api/bookings", methods=["GET"])
def list_bookings():
    # Only admins can view all bookings
    if session.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    bookings = (
        Booking.query.order_by(Booking.created_at.desc())
        if hasattr(Booking, "created_at")
        else Booking.query.all()
    )
    payload = [
        {
            "id": b.id,
            "movie_title": b.movie_title,
            "date": b.show_date,
            "showtime": b.showtime,
            "quantity": b.quantity,
            "user": b.booked_by,
            "created_at": b.created_at.isoformat() if getattr(b, "created_at", None) else None,
        }
        for b in bookings
    ]
    return jsonify({"bookings": payload})


def _validate_booking_payload(payload, allow_session_user=True):
    movie_title = payload.get("movie_title")
    show_date = payload.get("date") or payload.get("data")
    showtime_payload = payload.get("showtime") or {}
    showtime_time = showtime_payload.get("time")
    showtime_available_raw = showtime_payload.get("available")
    quantity_raw = payload.get("quantity")
    booked_by = payload.get("user") or payload.get("username") or (session.get("username") if allow_session_user else None)

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

    return {
        "movie_title": movie_title,
        "show_date": show_date,
        "showtime_time": showtime_time,
        "showtime_available": showtime_available,
        "quantity": quantity,
        "booked_by": booked_by,
        "errors": errors,
    }


@booking_bp.route("/api/bookings/checkout", methods=["POST"])
def create_checkout_session():
    # Create a Stripe Checkout session for booking payment
    username = session.get("username")
    if not username:
        return jsonify({"message": "Authentication required"}), 401

    if not stripe.api_key:
        return jsonify({"message": "Stripe not configured"}), 500

    payload = request.get_json() or {}
    validated = _validate_booking_payload(payload)
    if validated["errors"]:
        return jsonify({"message": "Invalid booking payload", "errors": validated["errors"]}), 400

    # Use per-ticket price; Stripe will multiply by quantity internally
    unit_amount = TICKET_PRICE_CENTS

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "cad",
                        "product_data": {
                            "name": f"{validated['movie_title']} — {validated['showtime_time']}",
                            "description": f"Date: {validated['show_date']}",
                        },
                        "unit_amount": unit_amount,
                    },
                    "quantity": validated["quantity"],
                }
            ],
            success_url=url_for("booking_api.checkout_success", _external=True)
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("booking_api.checkout_cancel", _external=True),
            metadata={
                "movie_title": validated["movie_title"],
                "date": validated["show_date"],
                "showtime": validated["showtime_time"],
                "quantity": str(validated["quantity"]),
                "user": validated["booked_by"],
            },
        )
    except Exception as exc:
        return jsonify({"message": "Failed to create checkout session", "error": str(exc)}), 500

    return jsonify({"checkout_url": checkout_session.url})


def _persist_booking_from_metadata(metadata):
    required_keys = ["movie_title", "date", "showtime", "quantity", "user"]
    if not all(key in metadata for key in required_keys):
        return None

    try:
        quantity = int(metadata.get("quantity"))
    except (TypeError, ValueError):
        quantity = None

    if quantity is None or quantity <= 0:
        return None

    existing = Booking.query.filter_by(
        movie_title=metadata.get("movie_title"),
        show_date=metadata.get("date"),
        showtime=metadata.get("showtime"),
        booked_by=metadata.get("user"),
        quantity=quantity,
    ).first()
    if existing:
        return existing

    booking = Booking(
        movie_title=metadata.get("movie_title"),
        show_date=metadata.get("date"),
        showtime=metadata.get("showtime"),
        quantity=quantity,
        booked_by=metadata.get("user"),
    )
    db.session.add(booking)
    db.session.commit()
    return booking


@booking_bp.route("/checkout/success")
def checkout_success():
    session_id = request.args.get("session_id")
    if not session_id:
        return render_template("checkout_success.html", booking=None, message="Missing session id")

    if not stripe.api_key:
        return render_template("checkout_success.html", booking=None, message="Stripe not configured")

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        return render_template("checkout_success.html", booking=None, message=f"Could not verify payment: {exc}")

    metadata = checkout_session.get("metadata", {}) if checkout_session else {}
    booking = None
    try:
        booking = _persist_booking_from_metadata(metadata)
    except Exception:
        db.session.rollback()
        return render_template("checkout_success.html", booking=None, message="Payment succeeded, but failed to save booking.")

    return render_template("checkout_success.html", booking=booking, message=None)


@booking_bp.route("/checkout/cancel")
def checkout_cancel():
    return render_template("checkout_cancel.html")


@booking_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not stripe.api_key or not webhook_secret:
        return "", 400

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return "", 400

    if event and event.get("type") == "checkout.session.completed":
        session_obj = event["data"]["object"]
        metadata = session_obj.get("metadata", {}) if session_obj else {}
        try:
            _persist_booking_from_metadata(metadata)
        except Exception:
            db.session.rollback()
            return "", 500

    return "", 200


@booking_bp.route("/api/bookings/<int:booking_id>", methods=["PUT", "PATCH"])
def update_booking(booking_id):
    # Only admins can update bookings
    if session.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"message": "Booking not found"}), 404

    original_booked_by = booking.booked_by

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

    # Never change who made the booking
    booking.booked_by = original_booked_by

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
    role = session.get("role")
    is_admin = role == "admin"

    if not username:
        return jsonify({"message": "Authentication required"}), 401

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"message": "Booking not found"}), 404
    if not is_admin and booking.booked_by != username:
        return jsonify({"message": "Not authorized to cancel this booking"}), 403

    try:
        db.session.delete(booking)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"message": "Failed to delete booking", "error": str(exc)}), 500

    return jsonify({"message": "Booking cancelled successfully", "booking_id": booking_id})
