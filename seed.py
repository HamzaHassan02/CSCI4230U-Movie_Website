import os
import requests
import bcrypt
from app import app, db
from models import User, Movie
from datetime import date, timedelta

OMDB_API_KEY = "225f5d3d"

seed_titles = [
    "Wicked: For Good",
    "Regretting You",
    "Black Phone 2",
    "Zootopia 2",
    "Predator: Badlands"
]

expiration = date.today() + timedelta(days=90)   # 3 months in theaters

def fetch_movie(title):
    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={title}&type=movie"
    data = requests.get(url).json()

    if not data or data.get("Response") == "False":
        return None

    # get first match
    first = data["Search"][0]
    
    # Now fetch full details using imdbID
    detail_url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={first['imdbID']}"
    return requests.get(detail_url).json()


def hash_password(password, pepper, salt=None):
    if salt is None:
        salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw((password + pepper).encode(), salt)
    return hashed, salt

with app.app_context():

    # ------------------------------
    # Seed Admin User
    # ------------------------------
    pepper = os.getenv("PEPPER")
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin123!")

    existing_admin = User.query.filter_by(username=admin_username).first()
    if not existing_admin:
        password_hash, salt = hash_password(admin_password, pepper)
        admin = User(
            username=admin_username,
            password_hash=password_hash,
            salt=salt,
            role="admin"
        )
        db.session.add(admin)
        print("Admin user created!")
    else:
        print("Admin user already exists")

    # ------------------------------
    # Seed Movies
    # ------------------------------
    for title in seed_titles:
        data = fetch_movie(title)
        imdb_id = data.get("imdbID")
            
        # Skip invalid movies
        if not data or data.get("Response") == "False":
            print(f"Skipping '{title}' — OMDB returned no results.")
            continue
        
        # Prevent duplicates
        if Movie.query.filter_by(imdb_id=imdb_id).first():
            print(f"Skipping {title} (already in DB)")
            continue

        movie = Movie(
            imdb_id=imdb_id,
            title=data.get("Title"),
            year=data.get("Year"),
            poster=data.get("Poster"),
            expiration=expiration
        )
        db.session.add(movie)
        print(f"Added movie: {title}")

    db.session.commit()
    print("Seeding complete!")
