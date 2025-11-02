
import sqlite3
from datetime import datetime

def init_db():
    """Initialize the SQLite database with required tables"""
    conn = sqlite3.connect('time_attack.db')
    cursor = conn.cursor()

    # Routes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Checkpoints table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            sequence_order INTEGER NOT NULL,
            FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE,
            UNIQUE(route_id, sequence_order)
        )
    """)

    # Runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            total_time_seconds REAL,
            notes TEXT,
            is_completed BOOLEAN DEFAULT 0,
            FOREIGN KEY (route_id) REFERENCES routes (id) ON DELETE CASCADE
        )
    """)

    # Checkpoint times table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoint_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            checkpoint_id INTEGER NOT NULL,
            time_reached TIMESTAMP NOT NULL,
            segment_time_seconds REAL NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE,
            FOREIGN KEY (checkpoint_id) REFERENCES checkpoints (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
