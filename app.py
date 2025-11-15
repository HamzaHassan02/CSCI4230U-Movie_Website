import os

from flask import Flask, render_template
from flask_jwt_extended import JWTManager, jwt_required
from dotenv import load_dotenv

from models import db
from routes.auth_routes import auth_bp

load_dotenv()

app = Flask(__name__)
# Configure SQLite Database
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")

db.init_app(app)

jwt = JWTManager(app)
app.register_blueprint(auth_bp)


# -----------------------
# Dummy Data (Temporary)
# -----------------------
dummy_poster = "/static/images/dummy_poster.png"
dummy_movies = [
    {
        "id": 1,
        "title": "Interstellar",
        "poster_url": dummy_poster,
        "director": "Christopher Nolan",
        "genre": "Sci-Fi",
        "rating": 8.6
    },
    {
        "id": 2,
        "title": "Inception",
        "poster_url": dummy_poster,
        "director": "Christopher Nolan",
        "genre": "Action",
        "rating": 8.8
    }
]

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

# -----------------------
# Routes
# -----------------------

@app.route("/")
def home_page():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html", movies=dummy_movies)

@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    movie = next((m for m in dummy_movies if m["id"] == movie_id), None)
    return render_template("movie.html", movie=movie)

@app.route("/booking/<int:movie_id>")
def booking(movie_id):
    movie = next((m for m in dummy_movies if m["id"] == movie_id), None)
    return render_template("booking.html", movie=movie, showtimes=dummy_showtimes)

@app.route("/my-bookings")
def bookings():
    return render_template("bookings.html", bookings=dummy_bookings)

@app.route("/admin")
@jwt_required()
def admin_dashboard():
    dummy_users = [
        {"username": "hamza", "booking_count": 3},
        {"username": "student", "booking_count": 1},
    ]
    return render_template("admin.html", users=dummy_users)

# -----------------------
# Run the app
# -----------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
