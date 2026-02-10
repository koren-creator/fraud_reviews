"""Database initialization and migrations"""
import sqlite3
import os
from config import DATABASE_PATH


def init_db():
    """Initialize the database with schema"""
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()

    cursor.executescript(schema)
    conn.commit()
    conn.close()

    print(f"Database initialized successfully at {DATABASE_PATH}")


if __name__ == '__main__':
    init_db()
