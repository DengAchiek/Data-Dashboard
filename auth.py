
import psycopg2
from psycopg2 import IntegrityError
import os
from werkzeug.security import generate_password_hash, check_password_hash

# Database Config (Render)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


# Initialize Users Table

def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(250) UNIQUE NOT NULL,
            password VARCHAR(200) NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()


# Register User

def register_user(email, password):
    hashed_password = generate_password_hash(password)
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, hashed_password)
        )
        conn.commit()
        cursor.close()
        return True
    except IntegrityError:
        if conn:
            conn.rollback()
        return False  # Email already exists
    finally:
        if conn:
            conn.close()

# Validate Login

def validate_login(email, password):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return check_password_hash(row[0], password)
    return False
