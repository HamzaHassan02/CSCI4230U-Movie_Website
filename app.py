import os, requests
from functools import wraps

from flask import Flask, redirect, render_template, session, url_for
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from dotenv import load_dotenv

from models import db
from routes.auth_routes import auth_bp

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


@app.context_processor
def inject_user_role():
    return {"current_user_role": session.get("role")}


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

movies_to_fetch = ["Interstellar", "Inception"]
dummy_movies = []

for idx, title in enumerate(movies_to_fetch, 1):
    data = get_movie_data(title)

    dummy_movies.append({
        "id": idx,
        "title": data.get("Title"),
        "poster_url": data.get("Poster"),
        "director": data.get("Director"),
        "genre": data.get("Genre"),
        "rating": data.get("imdbRating")
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

@app.route("/movie/<int:movie_id>")
@login_required_view
def movie_detail(movie_id):
    movie = next((m for m in dummy_movies if m["id"] == movie_id), None)
    return render_template("movie.html", movie=movie)

@app.route("/booking/<int:movie_id>")
@login_required_view
def booking(movie_id):
    movie = next((m for m in dummy_movies if m["id"] == movie_id), None)
    return render_template("booking.html", movie=movie, showtimes=dummy_showtimes)

@app.route("/my-bookings")
@login_required_view
def bookings():
    return render_template("bookings.html", bookings=dummy_bookings)

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
