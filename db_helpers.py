
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
                SELECT id, MIN(total_time_seconds) as best_time, start_time 
                FROM runs 
                WHERE route_id = ? AND is_completed = 1
                GROUP BY route_id
            """, (route_id,))
            row = cursor.fetchone()
            if row and row[1]:
                return {
                    'run_id': row[0],
                    'time_seconds': row[1],
                    'date': row[2]
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

    # NEW: Ghost comparison methods
    def get_run_checkpoint_times(self, run_id: int) -> List[Dict]:
        """Get all checkpoint times for a specific run"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    c.id,
                    c.name,
                    c.sequence_order,
                    ct.segment_time_seconds,
                    ct.time_reached
                FROM checkpoint_times ct
                JOIN checkpoints c ON ct.checkpoint_id = c.id
                WHERE ct.run_id = ?
                ORDER BY c.sequence_order
            """, (run_id,))

            checkpoints = []
            cumulative_time = 0
            for row in cursor.fetchall():
                cumulative_time += row[3]
                checkpoints.append({
                    'checkpoint_id': row[0],
                    'name': row[1],
                    'sequence_order': row[2],
                    'segment_time': row[3],
                    'cumulative_time': cumulative_time,
                    'time_reached': row[4]
                })
            return checkpoints
        finally:
            conn.close()

    def get_ghost_comparison(self, run_id: int, ghost_run_id: int) -> pd.DataFrame:
        """Compare two runs checkpoint by checkpoint"""
        current_checkpoints = self.get_run_checkpoint_times(run_id)
        ghost_checkpoints = self.get_run_checkpoint_times(ghost_run_id)

        comparison = []
        for current, ghost in zip(current_checkpoints, ghost_checkpoints):
            segment_delta = current['segment_time'] - ghost['segment_time']
            cumulative_delta = current['cumulative_time'] - ghost['cumulative_time']

            comparison.append({
                'checkpoint_name': current['name'],
                'sequence_order': current['sequence_order'],
                'current_segment': current['segment_time'],
                'ghost_segment': ghost['segment_time'],
                'segment_delta': segment_delta,
                'current_cumulative': current['cumulative_time'],
                'ghost_cumulative': ghost['cumulative_time'],
                'cumulative_delta': cumulative_delta
            })

        return pd.DataFrame(comparison)

    def get_pb_ghost_comparison(self, run_id: int) -> Optional[pd.DataFrame]:
        """Compare a run against personal best (ghost)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Get route_id for this run
            cursor.execute("SELECT route_id FROM runs WHERE id = ?", (run_id,))
            route_result = cursor.fetchone()
            if not route_result:
                return None

            route_id = route_result[0]

            # Get personal best run
            pb = self.get_personal_best(route_id)
            if not pb or pb['run_id'] == run_id:
                return None  # No PB or this IS the PB

            return self.get_ghost_comparison(run_id, pb['run_id'])
        finally:
            conn.close()

    def get_run_details(self, run_id: int) -> Optional[Dict]:
        """Get detailed information about a specific run"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    r.id,
                    r.route_id,
                    r.start_time,
                    r.end_time,
                    r.total_time_seconds,
                    r.notes,
                    r.is_completed,
                    rt.name as route_name
                FROM runs r
                JOIN routes rt ON r.route_id = rt.id
                WHERE r.id = ?
            """, (run_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'route_id': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'total_time_seconds': row[4],
                    'notes': row[5],
                    'is_completed': bool(row[6]),
                    'route_name': row[7]
                }
            return None
        finally:
            conn.close()

    def delete_run(self, run_id: int):
        """Delete a run and all associated checkpoint times"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            conn.commit()
        finally:
            conn.close()


    def get_live_ghost_data(self, route_id: int) -> Optional[List[Dict]]:
        """Get personal best checkpoint times for live ghost comparison"""
        pb = self.get_personal_best(route_id)
        if not pb:
            return None
        return self.get_run_checkpoint_times(pb['run_id'])
