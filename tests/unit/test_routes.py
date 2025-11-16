import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt")
os.environ.setdefault("PEPPER", "test-pepper")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app import app, db
from models import User


@pytest.fixture()
def client(tmp_path):
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'unit.db'}",
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_home_page_renders_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to MovieReservation" in response.data

# valid registration test
def test_register_creates_valid_user(client):
    payload = {"username": "unit_user", "password": "secret123!"}
    response = client.post("/register", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    with app.app_context():
        assert User.query.filter_by(username="unit_user").count() == 1

#duplicate registration test
def test_duplicate_register_returns_conflict(client):
    payload = {"username": "dup_user", "password": "secret123!"}
    client.post("/register", data=json.dumps(payload), content_type="application/json")
    response = client.post("/register", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 409

#invalid username registration tests
def test_register_invalid_username_valid_password(client):
    payload = {"username": "inv@lid", "password": "Valid123!"}
    response = client.post("/register", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    body = response.get_json()
    assert body["message"] == "Invalid input"
    username_errors = [error["msg"] for error in body["errors"] if error["field"] == "username"]
    assert "Username may only contain letters, numbers, and underscores" in username_errors

def test_register_short_username(client):
    payload = {"username": "abc", "password": "Valid123!"}
    response = client.post("/register", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    body = response.get_json()
    assert body["message"] == "Invalid input"
    username_errors = [error["msg"] for error in body["errors"] if error["field"] == "username"]
    assert "Username must have at least 4 characters" in username_errors

#invalid password registration tests
def test_register_validation_errors(client):
    payload = {"username": "ab", "password": "123"}
    response = client.post("/register", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    body = response.get_json()
    assert body["message"] == "Invalid input"
    username_errors = [error["msg"] for error in body["errors"] if error["field"] == "username"]
    password_errors = [error["msg"] for error in body["errors"] if error["field"] == "password"]
    assert "Username must have at least 4 characters" in username_errors
    assert "Password must be at least 8 characters" in password_errors

def test_register_no_number_in_password(client):
    payload = {"username": "validuser", "password": "NoNumber!"}
    response = client.post("/register", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    body = response.get_json()
    assert body["message"] == "Invalid input"
    password_errors = [error["msg"] for error in body["errors"] if error["field"] == "password"]
    assert "Password must have a number" in password_errors

def test_register_valid_username_no_special_character_in_password(client):
    payload = {"username": "validuser", "password": "shorttt1"}
    response = client.post("/register", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    body = response.get_json()
    assert body["message"] == "Invalid input"
    password_errors = [error["msg"] for error in body["errors"] if error["field"] == "password"]
    assert "Password must have at least 1 special character" in password_errors

# VALID LOGIN
def test_login_with_valid_credentials(client):
    register_payload = {"username": "login_user", "password": "Valid123!"}

    # First register the user
    client.post("/register", data=json.dumps(register_payload), content_type="application/json")

    # Now login
    login_payload = {"username": "login_user", "password": "Valid123!"}
    response = client.post("/login", data=json.dumps(login_payload), content_type="application/json")

    assert response.status_code == 200
    body = response.get_json()
    assert "token" in body

# INVALID PASSWORD
def test_login_with_invalid_password(client):
    register_payload = {"username": "user2", "password": "Valid123!"}
    client.post("/register", data=json.dumps(register_payload), content_type="application/json")

    login_payload = {"username": "user2", "password": "WrongPass1!"}
    response = client.post("/login", data=json.dumps(login_payload), content_type="application/json")

    assert response.status_code == 401
    body = response.get_json()
    assert body["message"] == "Invalid password"


# USER DOES NOT EXIST
def test_login_user_not_found(client):
    login_payload = {"username": "ghost", "password": "Valid123!"}
    response = client.post("/login", data=json.dumps(login_payload), content_type="application/json")

    assert response.status_code == 404
    body = response.get_json()
    assert body["message"] == "User not found"
