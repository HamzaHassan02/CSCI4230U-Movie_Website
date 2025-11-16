import os

import bcrypt
from dotenv import load_dotenv
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token
from marshmallow import ValidationError

from models import db, User
from schemas import register_schema

load_dotenv()

pepper_value = os.getenv("PEPPER")
if pepper_value is None:
    raise RuntimeError("PEPPER environment variable is not set.")
PEPPER = pepper_value.encode('utf-8')

auth_bp = Blueprint("auth", __name__)


def hash_password(password):
    salt = bcrypt.gensalt()
    password_with_pepper = password.encode('utf-8') + PEPPER
    hashed_password = bcrypt.hashpw(password_with_pepper, salt)
    return hashed_password, salt


def verify_password(entered_password, stored_hashed_password, stored_salt):
    entered_password_with_pepper = entered_password.encode('utf-8') + PEPPER
    hashed_entered_password = bcrypt.hashpw(entered_password_with_pepper, stored_salt)
    return hashed_entered_password == stored_hashed_password


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register_page.html")

    try:
        payload = register_schema.load(request.get_json() or {})
    except ValidationError as exc:
        errors = []
        for field, messages in (exc.messages or {}).items():
            for message in messages:
                errors.append({"field": field, "msg": message})
        return jsonify({'message': 'Invalid input', 'errors': errors}), 400

    username = payload["username"]
    password = payload["password"]

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists'}), 409

    try:
        hashed_password, salt = hash_password(password)
        new_user = User(username=username, password_hash=hashed_password, salt=salt)
        db.session.add(new_user)
        db.session.commit()
    except Exception as exc:
        return jsonify({'message': 'Registration failed', 'error': str(exc)}), 500

    return jsonify({'message': 'User registered successfully'}), 201


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect(url_for("home_page"))

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if verify_password(password, user.password_hash, user.salt):
        token = create_access_token(identity=username)
        return jsonify({'message': 'Successful login', 'token': token}), 200

    return jsonify({'message': 'Invalid password'}), 401
