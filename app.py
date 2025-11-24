import os, requests
from functools import wraps

from flask import Flask, redirect, render_template, session, url_for
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from dotenv import load_dotenv

from models import Booking, db
from routes.auth_routes import auth_bp
from routes.booking_routes import booking_bp
from models import User

load_dotenv()

OMDB_API_KEY = "225f5d3d"
OMDB_URL = "http://www.omdbapi.com/"

app = Flask(__name__)
# Configure SQLite Database
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_CSRF_PROTECT"] = False

db.init_app(app)

jwt = JWTManager(app)
app.register_blueprint(auth_bp)
app.register_blueprint(booking_bp)

with app.app_context():
    db.create_all()
    # Seed admin user if missing to ensure admin access is available
    pepper_value = os.getenv("PEPPER")
    if pepper_value:
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")
        existing_admin = User.query.filter_by(username=admin_username).first()
        if not existing_admin:
            import bcrypt

            def hash_password(password: str, pepper: bytes):
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(password.encode("utf-8") + pepper, salt)
                return hashed, salt

            password_hash, salt = hash_password(admin_password, pepper_value.encode("utf-8"))
            admin_user = User(username=admin_username, password_hash=password_hash, salt=salt, role="admin")
            db.session.add(admin_user)
            db.session.commit()

@app.context_processor
def inject_user_context():
    return {
        "current_user_role": session.get("role"),
        "current_username": session.get("username"),
    }


# -----------------------
# Dummy Data (Temporary)
# -----------------------
def get_movie_data(title):
    params = {
        "t": title,
        "apikey": OMDB_API_KEY
    }
    response = requests.get(OMDB_URL, params=params)
    return response.json()

movies_to_fetch = [
    "Interstellar",
    "Inception",
    "The Dark Knight",
    "Avatar",
    "Avengers: Endgame",
    "Oppenheimer",
    "Bullet Train",
    "The Matrix",
    "The Shawshank Redemption",
    "Pulp Fiction",
    "The Lord of the Rings: The Fellowship of the Ring",
    "Spider-Man: No Way Home",
    "Joker",
    "Guardians of the Galaxy"
]

dummy_movies = []

for idx, title in enumerate(movies_to_fetch, 1):
    data = get_movie_data(title)

    dummy_movies.append({
        "id": data.get("imdbID"),
        "title": data.get("Title"),
        "poster_url": data.get("Poster"),
        "director": data.get("Director"),
        "studio": data.get("Production"),
        "genre": data.get("Genre"),
        "rating": data.get("imdbRating"),
        "runtime": data.get("Runtime"),
        "actors": data.get("Actors"),
        "plot": data.get("Plot"),
        "released": data.get("Released"),
    })

dummy_bookings = [
    {
        "id": 10,
        "movie_title": "Interstellar",
        "datetime": "Feb 14, 2025 - 7:00 PM",
        "quantity": 2
    }
]

dummy_showtimes = [
    {"time": "2:00 PM", "available": 15},
    {"time": "5:30 PM", "available": 9},
    {"time": "8:00 PM", "available": 20},
]

def login_required_view(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("home_page"))
        return fn(*args, **kwargs)

    return wrapper


@app.route("/")
def home_page():
    return render_template("index.html")

@app.route("/home")
@login_required_view
def home():
    return render_template("home.html", movies=dummy_movies)

@app.route("/movie/<movie_id>")
@login_required_view
def movie_detail(movie_id):
    movie = next((m for m in dummy_movies if m["id"] == movie_id), None)
    return render_template("movie.html", movie=movie)

@app.route("/booking/<movie_id>")
@login_required_view
def booking(movie_id):
    movie = next((m for m in dummy_movies if m["id"] == movie_id), None)
    return render_template("booking.html", movie=movie, showtimes=dummy_showtimes, existing_booking=None)


@app.route("/booking/edit/<int:booking_id>")
@login_required_view
def edit_booking(booking_id):
    username = session.get("username")
    if not username:
        return redirect(url_for("auth.login"))

    booking_record = Booking.query.get_or_404(booking_id)
    if booking_record.booked_by != username:
        return redirect(url_for("bookings"))

    movie = next((m for m in dummy_movies if m["title"] == booking_record.movie_title), None)
    if not movie:
        movie = {
            "id": 0,
            "title": booking_record.movie_title,
            "poster_url": "",
            "director": "",
            "genre": "",
            "rating": "",
        }

    existing_booking = {
        "id": booking_record.id,
        "show_date": booking_record.show_date,
        "showtime": booking_record.showtime,
        "quantity": booking_record.quantity,
    }

    return render_template("booking.html", movie=movie, showtimes=dummy_showtimes, existing_booking=existing_booking)

@app.route("/my-bookings")
@login_required_view
def bookings():
    username = session.get("username")
    if not username:
        return redirect(url_for("auth.login"))

    user_bookings = (
        Booking.query.filter_by(booked_by=username)
        .order_by(Booking.created_at.desc())
        .all()
    )
    booking_payload = [
        {
            "id": b.id,
            "movie_title": b.movie_title,
            "show_date": b.show_date,
            "showtime": b.showtime,
            "quantity": b.quantity,
            "booked_by": b.booked_by,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in user_bookings
    ]
    return render_template(
        "bookings.html",
        bookings=user_bookings,
        username=username,
        bookings_payload=booking_payload,
    )

@app.route("/admin")
@login_required_view
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("home"))
    dummy_users = [
        {"username": "hamza", "booking_count": 3},
        {"username": "student", "booking_count": 1},
    ]
    return render_template("admin.html", users=dummy_users)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
