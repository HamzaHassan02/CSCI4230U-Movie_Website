import os, requests
from models import Movie

OMDB_API_KEY = "225f5d3d"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")

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
