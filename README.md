# CSCI4230U-Movie_Website
Movie Website for Final Group Project of CSCI 4230U Advanced Web Development Fall 2025.

### Group Members
- Hamza Hassan (100788913)
- Abdullah Mohammed (100784442)

## How to Run
1. Create and enter virtual environment
```
python -m venv venv
source venv/bin/activate # or for windows source venv/Scripts/activate
```
2. Install dependencies
```
pip install -r requirements.txt
```
3. Create your environment variables  
Make a copy of `.env.example` and rename it to `.env`:

```
cp .env.example .env
```

Then open `.env` and fill in:

```
SECRET_KEY=your_flask_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
PEPPER=your_pepper_value
DATABASE_URL=sqlite:///database.db
```

4. Start app
```
python app.py
```
