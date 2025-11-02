# Create the database helper functions
db_helpers_code = '''
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import pandas as pd

class TimeAttackDB:
    def __init__(self, db_path: str = "time_attack.db"):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    # Route management
    def create_route(self, name: str, description: str = "") -> int:
        """Create a new route and return its ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO routes (name, description) VALUES (?, ?)", (name, description))
            route_id = cursor.lastrowid
            conn.commit()
            return route_id
        finally:
            conn.close()
    
    def get_routes(self) -> List[Dict]:
        """Get all routes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, name, description, created_at FROM routes ORDER BY name")
            routes = []
            for row in cursor.fetchall():
                routes.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created_at': row[3]
                })
            return routes
        finally:
            conn.close()
    
    def delete_route(self, route_id: int):
        """Delete a route and all associated data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM routes WHERE id = ?", (route_id,))
            conn.commit()
        finally:
            conn.close()
    
    # Checkpoint management
    def add_checkpoint(self, route_id: int, name: str, sequence_order: int):
        """Add a checkpoint to a route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO checkpoints (route_id, name, sequence_order) VALUES (?, ?, ?)",
                (route_id, name, sequence_order)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_checkpoints(self, route_id: int) -> List[Dict]:
        """Get all checkpoints for a route in sequence order"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, name, sequence_order FROM checkpoints WHERE route_id = ? ORDER BY sequence_order",
                (route_id,)
            )
            checkpoints = []
            for row in cursor.fetchall():
                checkpoints.append({
                    'id': row[0],
                    'name': row[1],
                    'sequence_order': row[2]
                })
            return checkpoints
        finally:
            conn.close()
    
    def delete_checkpoint(self, checkpoint_id: int):
        """Delete a checkpoint"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM checkpoints WHERE id = ?", (checkpoint_id,))
            conn.commit()
        finally:
            conn.close()
    
    # Run management
    def start_run(self, route_id: int, notes: str = "") -> int:
        """Start a new run and return its ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            start_time = datetime.now()
            cursor.execute(
                "INSERT INTO runs (route_id, start_time, notes) VALUES (?, ?, ?)",
                (route_id, start_time, notes)
            )
            run_id = cursor.lastrowid
            conn.commit()
            return run_id
        finally:
            conn.close()
    
    def complete_run(self, run_id: int, total_time_seconds: float):
        """Complete a run with total time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            end_time = datetime.now()
            cursor.execute(
                "UPDATE runs SET end_time = ?, total_time_seconds = ?, is_completed = 1 WHERE id = ?",
                (end_time, total_time_seconds, run_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    def record_checkpoint_time(self, run_id: int, checkpoint_id: int, segment_time_seconds: float):
        """Record time for reaching a checkpoint"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            time_reached = datetime.now()
            cursor.execute(
                "INSERT INTO checkpoint_times (run_id, checkpoint_id, time_reached, segment_time_seconds) VALUES (?, ?, ?, ?)",
                (run_id, checkpoint_id, time_reached, segment_time_seconds)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_current_run(self, run_id: int) -> Optional[Dict]:
        """Get current run details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, route_id, start_time, is_completed FROM runs WHERE id = ?",
                (run_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'route_id': row[1],
                    'start_time': datetime.fromisoformat(row[2]),
                    'is_completed': bool(row[3])
                }
            return None
        finally:
            conn.close()
    
    # Analytics
    def get_personal_best(self, route_id: int) -> Optional[Dict]:
        """Get personal best time for a route"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MIN(total_time_seconds), start_time 
                FROM runs 
                WHERE route_id = ? AND is_completed = 1
            """, (route_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return {
                    'time_seconds': row[0],
                    'date': row[1]
                }
            return None
        finally:
            conn.close()
    
    def get_run_history(self, route_id: int) -> pd.DataFrame:
        """Get run history for a route"""
        conn = self.get_connection()
        try:
            query = """
                SELECT 
                    r.id,
                    r.start_time,
                    r.total_time_seconds,
                    r.notes,
                    DATE(r.start_time) as run_date
                FROM runs r
                WHERE r.route_id = ? AND r.is_completed = 1
                ORDER BY r.start_time DESC
            """
            return pd.read_sql_query(query, conn, params=(route_id,))
        finally:
            conn.close()
    
    def get_checkpoint_analysis(self, route_id: int) -> pd.DataFrame:
        """Get checkpoint performance analysis"""
        conn = self.get_connection()
        try:
            query = """
                SELECT 
                    c.name as checkpoint_name,
                    c.sequence_order,
                    AVG(ct.segment_time_seconds) as avg_time,
                    MIN(ct.segment_time_seconds) as best_time,
                    MAX(ct.segment_time_seconds) as worst_time,
                    COUNT(*) as times_completed
                FROM checkpoints c
                LEFT JOIN checkpoint_times ct ON c.id = ct.checkpoint_id
                LEFT JOIN runs r ON ct.run_id = r.id
                WHERE c.route_id = ? AND r.is_completed = 1
                GROUP BY c.id, c.name, c.sequence_order
                ORDER BY c.sequence_order
            """
            return pd.read_sql_query(query, conn, params=(route_id,))
        finally:
            conn.close()
'''

# Save database helpers
with open('db_helpers.py', 'w') as f:
    f.write(db_helpers_code)

print("✓ Created db_helpers.py")