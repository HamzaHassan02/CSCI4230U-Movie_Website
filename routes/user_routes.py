from flask import Blueprint, jsonify, session

from models import Booking, User, db

user_bp = Blueprint("user_api", __name__)


@user_bp.route("/api/users", methods=["GET"])
def list_users():
    # Only admins can view all users
    if session.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    users = User.query.order_by(User.id.asc()).all()
    payload = [
        {"id": user.id, "username": user.username, "role": user.role}
        for user in users
    ]
    return jsonify({"users": payload})


@user_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    # Only admins can delete users
    if session.get("role") != "admin":
        return jsonify({"message": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    try:
        deleted_bookings = Booking.query.filter_by(booked_by=user.username).delete()
        db.session.delete(user)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"message": "Failed to delete user", "error": str(exc)}), 500

    return jsonify(
        {
            "message": "User deleted successfully",
            "user_id": user_id,
            "deleted_bookings": deleted_bookings,
        }
    )
