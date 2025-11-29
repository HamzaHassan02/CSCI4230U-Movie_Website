from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    salt = db.Column(db.LargeBinary, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')


class Booking(db.Model):
    __tablename__ = 'movie_bookings'
    id = db.Column(db.Integer, primary_key=True)
    movie_title = db.Column(db.String(255), nullable=False)
    show_date = db.Column(db.String(50), nullable=False)
    showtime = db.Column(db.String(50), nullable=False)
    showtime_available = db.Column(db.Integer)
    quantity = db.Column(db.Integer, nullable=False)
    booked_by = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    imdb_id = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.String(10), nullable=False)
    poster = db.Column(db.String(300), nullable=False)
