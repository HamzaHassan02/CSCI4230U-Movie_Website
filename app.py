import datetime
from flask import Flask, render_template, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import bcrypt

PEPPER = b'secret_pepper_value'

app = Flask(__name__)
# Configure SQLite Database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)


#password hashing functions
def hash_password(password):
    salt = bcrypt.gensalt() # Generate salt using bcrypt.gensalt()
    password_with_pepper = password.encode('utf-8') + PEPPER # Combine password and PEPPER
    hashed_password = bcrypt.hashpw(password_with_pepper, salt) # Use bcrypt.hashpw() to hash the password_with_pepper and salt
    return hashed_password, salt

def verify_password(entered_password, stored_hashed_password, stored_salt):
    entered_password_with_pepper = entered_password.encode('utf-8') + PEPPER # Combine entered_password and PEPPER
    hashed_entered_password = bcrypt.hashpw(entered_password_with_pepper, stored_salt) # Use bcrypt.hashpw() to hash the entered password with the stored_salt
    return hashed_entered_password == stored_hashed_password # Compare hashed_entered_password with stored_hashed_password

#jwt functions
def create_jwt(username):
    payload = {
        'sub': username,
        'iat': datetime.datetime.utcnow(), # Set the issued-at time to the current UTC time
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30) # Set the expiration time to 30 minutes from now
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256') # Use jwt.encode() to create a JWT token with the payload and the secret key
    return token

#models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    salt = db.Column(db.LargeBinary, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')


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

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register_page.html")
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'message': 'User already exists'}), 409  # Respond with an error message (User already exists)
        
        try: 
            hashed_password, salt = hash_password(password)  # Call the hash_password function to hash the password
            new_user = User(username=username, password_hash=hashed_password, salt=salt)  # Create a new User object with the username, hashed_password, and salt
            db.session.add(new_user)  # Add the new user to the database
            db.session.commit()  # Commit the changes
        except Exception as e:
            return jsonify({'message': 'Registration failed', 'error': str(e)}), 500  # Respond with an error message if registration fails

        return jsonify({'message': 'User registered successfully'}), 201


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login_page.html")
    
    if request.method == "POST":
        data = request.get_json()
        username = data.get('username')  # Extract 'username' from the request data
        password = data.get('password')  # Extract 'password' from the request data and encode it

        # Query the database to get the user by username
        user = User.query.filter_by(username=username).first()

        if not user:
            return jsonify({'message': 'User does not exist'}), 404  # Respond with an error message (User does not exist)

        # Verify the password using the verify_password function
        if verify_password(password, user.password_hash, user.salt):
            token = create_jwt(username)  # Call the create_jwt function to generate a JWT token for the user
            return jsonify({'message': 'Successful login', 'token': token}), 200  # Respond with a success message and the token
        else:
            return jsonify({'message': 'Invalid password'}), 401  # Respond with an error message (Invalid password)

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
