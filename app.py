import os, requests
from functools import wraps

from flask import Flask, redirect, render_template, session, url_for, request
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from dotenv import load_dotenv
from datetime import date, datetime, timedelta

from models import Booking, Movie, db
from routes.auth_routes import auth_bp
from routes.booking_routes import booking_bp
from routes.user_routes import user_bp
from models import User

load_dotenv()

OMDB_API_KEY = "225f5d3d"
OMDB_URL = "http://www.omdbapi.com/"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")

set_showtimes = [
    {"time": "2:00 PM", "available": 15},
    {"time": "5:30 PM", "available": 9},
    {"time": "8:00 PM", "available": 20},
]

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
app.register_blueprint(user_bp)

with app.app_context():
    db.create_all()

@app.context_processor
def inject_user_context():
    return {
        "current_user_role": session.get("role"),
        "current_username": session.get("username"),
    }

def login_required_view(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return redirect(url_for("home_page"))
        return fn(*args, **kwargs)

    return wrapper

# Chatbot functions 
def build_movie_knowledge():
    """Return detailed movie summaries using both DB and OMDB."""
    movies = Movie.query.all()
    if not movies:
        return "No movies available."

    details = []
    for m in movies:
        try:
            omdb_data = requests.get(
                f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={m.imdb_id}&plot=short"
            ).json()

            actors = omdb_data.get("Actors", "Unknown actors")
            genre = omdb_data.get("Genre", "Unknown genre")
            plot = omdb_data.get("Plot", "No plot available")
            rating = omdb_data.get("imdbRating", "N/A")

            details.append(
                f"Title: {m.title}. Genre: {genre}. Actors: {actors}. "
                f"Rating: {rating}. Plot: {plot}"
            )

        except Exception as e:
            print("Error occured:", e)
            details.append(f"Title: {m.title}. Limited info available.")

    return "\n".join(details)



def ask_movie_bot(user_message: str) -> str:
    """Send a prompt to Ollama using the movies in the DB as context."""
    context = build_movie_knowledge()

    prompt = f"""
                You are FlickBook's concise movie assistant.

                Use ONLY the movie data provided below. 
                If the user asks about movies, an actor, genre, rating, or plot, check the provided movie list.

                Keep answers SHORT:
                - 1 to 2 sentences
                - Directly answer the question
                - Do NOT include long lists or summaries unless asked

                Movie Data:
                {context}

                User: {user_message}
            """.strip()

    try:
        res = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        res.raise_for_status()
        data = res.json()
        reply = data.get("response") or "Sorry, I couldn't generate a response."
        return reply.strip()
    except Exception as e:
        print("Ollama error:", e)
        return "LLM Error."


# -----------------------
# Routes
# -----------------------
@app.route("/")
def home_page():
    return render_template("index.html") # route to login page

@app.route("/home")
@login_required_view
def home():
    movies = Movie.query.all()
    return render_template("home.html", movies=movies)

@app.route("/api/chat", methods=["POST"])
@login_required_view
def movie_chat():
    if not request.is_json:
        return {"error": "JSON body required"}, 400

    message = (request.json.get("message") or "").strip()
    if not message:
        return {"error": "Empty message"}, 400

    answer = ask_movie_bot(message)
    return {"reply": answer}

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
    return render_template(
        "booking.html", movie=movie, 
        showtimes=set_showtimes, 
        existing_booking=None, 
        today=date.today().isoformat()        
    )


@app.route("/booking/edit/<int:booking_id>")
@login_required_view
def edit_booking(booking_id):
    username = session.get("username")
    is_admin = session.get("role") == "admin"
    if not username:
        return redirect(url_for("auth.login"))

    booking_record = Booking.query.get_or_404(booking_id)
    if not is_admin and booking_record.booked_by != username:
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

    return render_template(
        "booking.html",
        movie=movie,
        showtimes=set_showtimes,
        existing_booking=existing_booking,
        today=date.today().isoformat()
    )

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
    week = (date.today() + timedelta(days=7)).isoformat()
    return render_template("manage_movies.html", movies=movies, week=week)

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
    expiration_str = data.get("expiration")
    
    expiration = None
    if expiration_str:
        expiration = datetime.strptime(expiration_str, "%Y-%m-%d").date()

    # Check DB duplicate
    existing_movie = Movie.query.filter_by(imdb_id=imdb_id).first()
    if existing_movie:
        return {"message": "Movie already added"}

    # Save to DB
    new_movie = Movie(
        imdb_id=imdb_id,
        title=title,
        year=year,
        poster=poster,
        expiration=expiration
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
