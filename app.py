import os, requests
from functools import wraps

from flask import Flask, redirect, render_template, session, url_for, request
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from dotenv import load_dotenv

from models import Booking, Movie, db
from routes.auth_routes import auth_bp
from routes.booking_routes import booking_bp

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

@app.context_processor
def inject_user_context():
    return {
        "current_user_role": session.get("role"),
        "current_username": session.get("username"),
    }


# -----------------------
# Dummy Data (Temporary)
# -----------------------
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
    return render_template("index.html") # route to login page

@app.route("/home")
@login_required_view
def home():
    movies = Movie.query.all()
    return render_template("home.html", movies=movies)

@app.route("/movie/<movie_id>")
@login_required_view
def movie_detail(movie_id):
    # Get movie from DB (does not contain full movie data)
    movie = Movie.query.filter_by(imdb_id=movie_id).first()
    if not movie:
        return "Movie not found", 404

    # Fetch full OMDB data
    omdb_data = requests.get(
        f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={movie.imdb_id}&plot=full"
    ).json()

    # Build a full movie detail object
    movie_details = {
        "title": movie.title,
        "poster": omdb_data.get("Poster"),
        "director": omdb_data.get("Director"),
        "studio": omdb_data.get("Production"),
        "genre": omdb_data.get("Genre"),
        "rating": omdb_data.get("imdbRating"),
        "runtime": omdb_data.get("Runtime"),
        "actors": omdb_data.get("Actors"),
        "plot": omdb_data.get("Plot"),
        "released": omdb_data.get("Released"),
        "imdb_id": movie.imdb_id
    }

    return render_template("movie.html", movie=movie_details)

@app.route("/booking/<movie_id>")
@login_required_view
def booking(movie_id):
    movie = Movie.query.filter_by(imdb_id=movie_id).first()
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

    movie = Movie.query.filter_by(title=booking_record.movie_title).first()
    if not movie:
        movie = {
            "id": 0,
            "title": booking_record.movie_title,
            "poster": "",
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

@app.route("/admin/manage-movies")
@login_required_view
def manage_movies():
    # Only admin allowed
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    movies = Movie.query.all()
    return render_template("manage_movies.html", movies=movies)

@app.route("/admin/search-movies", methods=["GET"])
@login_required_view
def search_movies():
    if session.get("role") != "admin":
        return {"error": "Unauthorized"}, 403

    query = request.args.get("q", "")
    if not query:
        return {"error": "Missing query"}, 400

    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={query}&type=movie"
    res = requests.get(url).json()

    if res.get("Response") == "False":
        return {"results": []}

    return {"results": res.get("Search", [])}

@app.route("/admin/add-movie", methods=["POST"])
@login_required_view
def add_movie():
    if session.get("role") != "admin":
        return {"error": "Unauthorized"}, 403

    data = request.json
    imdb_id = data.get("imdb_id")
    title = data.get("title")
    year = data.get("year")
    poster = data.get("poster")

    # Check DB duplicate
    existing_movie = Movie.query.filter_by(imdb_id=imdb_id).first()
    if existing_movie:
        return {"message": "Movie already added"}

    # Save to DB
    new_movie = Movie(
        imdb_id=imdb_id,
        title=title,
        year=year,
        poster=poster
    )
    db.session.add(new_movie)
    db.session.commit()

    return {"message": "Movie added"}

@app.route("/admin/remove-movie", methods=["POST"])
@login_required_view
def remove_movie():
    if session.get("role") != "admin":
        return {"error": "Unauthorized"}, 403

    data = request.json
    imdb_id = data.get("imdb_id")

    movie = Movie.query.filter_by(imdb_id=imdb_id).first()
    if movie:
        db.session.delete(movie)
        db.session.commit()

    return {"message": "Movie removed"}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
