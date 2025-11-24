from supabase import create_client
from datetime import datetime
import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class TimeAttackDB:
    # ----- Route management -----
    def create_route(self, name, description=""):
        result = supabase.table("routes").insert(
            {"name": name, "description": description}
        ).execute()
        return result.data[0]['id']

    def get_routes(self):
        routes = supabase.table("routes").select("*").order("name").execute().data
        return routes

    def delete_route(self, route_id):
        supabase.table("routes").delete().eq("id", route_id).execute()

    # ----- Checkpoint management -----
    def add_checkpoint(self, route_id, name, sequence_order):
        supabase.table("checkpoints").insert(
            {"route_id": route_id, "name": name, "sequence_order": sequence_order}
        ).execute()

    def get_checkpoints(self, route_id):
        return (
            supabase.table("checkpoints")
            .select("*")
            .eq("route_id", route_id)
            .order("sequence_order")
            .execute()
            .data
        )

    def delete_checkpoint(self, checkpoint_id):
        supabase.table("checkpoints").delete().eq("id", checkpoint_id).execute()

    # ----- Run management -----
    def start_run(self, route_id, notes=""):
        now = datetime.utcnow().isoformat()
        result = supabase.table("runs").insert(
            {"route_id": route_id, "start_time": now, "notes": notes, "is_completed": 0}
        ).execute()
        return result.data[0]['id']

    def complete_run(self, run_id, total_time_seconds):
        now = datetime.utcnow().isoformat()
        supabase.table("runs").update(
            {"total_time_seconds": total_time_seconds, "is_completed": 1}
        ).eq("id", run_id).execute()

    def delete_run(self, run_id):
        supabase.table("runs").delete().eq("id", run_id).execute()

    # ----- Checkpoint times -----
    def record_checkpoint_time(self, run_id, checkpoint_id, segment_time_seconds):
        now = datetime.utcnow().isoformat()
        supabase.table("checkpoint_times").insert(
            {
                "run_id": run_id,
                "checkpoint_id": checkpoint_id,
                "time_reached": now,
                "segment_time": segment_time_seconds,
            }
        ).execute()

    # ----- Retrieving run/checkpoint/run details for logic -----
    def get_latest_active_run(self):
        res = (
            supabase.table("runs")
            .select("id, route_id")
            .eq("is_completed", 0)
            .order("start_time", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def get_run_details(self, run_id):
        res = (
            supabase.table("runs")
            .select("*")
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def get_run_checkpoint_times(self, run_id):
        cps = (
            supabase.table("checkpoint_times")
            .select("*, checkpoint_id")
            .eq("run_id", run_id)
            .order("id")  # preserves original sequence order if ids come in order
            .execute()
            .data
        )
        if not cps:
            return []
        # For cumulative time calc
        checkpoints = []
        cumulative_time = 0
        for cp in cps:
            seg_time = cp["segment_time"]
            cumulative_time += seg_time if seg_time is not None else 0
            checkpoints.append({
                "checkpoint_id": cp.get("checkpoint_id"),
                "segment_time": seg_time,
                "cumulative_time": cumulative_time,
                "time_reached": cp.get("time_reached")
            })
        return checkpoints

    # ----- Analytics -----
    def get_personal_best(self, route_id):
        res = (
            supabase.table("runs")
            .select("id, total_time_seconds, start_time")
            .eq("route_id", route_id)
            .eq("is_completed", 1)
            .order("total_time_seconds")
            .limit(1)
            .execute()
        )
        if res.data and res.data[0]['total_time_seconds'] is not None:
            return {
                "run_id": res.data[0]["id"],
                "time_seconds": res.data[0]["total_time_seconds"],
                "date": res.data[0]["start_time"]
            }
        return None

    def get_run_history(self, route_id):
        res = (
            supabase.table("runs")
            .select("*")
            .eq("route_id", route_id)
            .eq("is_completed", 1)
            .order("start_time", desc=True)
            .execute()
        )
        df = pd.DataFrame(res.data)
        return df if not df.empty else pd.DataFrame([])

    def get_checkpoint_analysis(self, route_id):
        # Aggregation has to be done in pandas since Supabase-py does not support SQL aggregation
        cps = (
            supabase.table("checkpoints")
            .select("id, name, sequence_order")
            .eq("route_id", route_id)
            .order("sequence_order")
            .execute()
            .data
        )
        if not cps:
            return pd.DataFrame([])

        all_segs = []
        for cp in cps:
            ct = (
                supabase.table("checkpoint_times")
                .select("segment_time")
                .eq("checkpoint_id", cp["id"])
                .execute().data
            )
            times = [t['segment_time'] for t in ct if t['segment_time'] is not None]
            all_segs.append({
                "Checkpoint": cp['name'],
                "Order": cp['sequence_order'],
                "avg_time": sum(times)/len(times) if times else None,
                "best_time": min(times) if times else None,
                "worst_time": max(times) if times else None,
                "Completed": len(times)
            })
        return pd.DataFrame(all_segs)

    # ----- Ghost logic -----
    def get_ghost_comparison(self, run_id, ghost_run_id):
        current = self.get_run_checkpoint_times(run_id)
        ghost = self.get_run_checkpoint_times(ghost_run_id)
        comparison = []
        for curr, gh in zip(current, ghost):
            seg_delta = (curr['segment_time'] or 0) - (gh['segment_time'] or 0)
            cum_delta = (curr['cumulative_time'] or 0) - (gh['cumulative_time'] or 0)
            comparison.append({
                "checkpoint_name": curr.get("name", "Unknown"),  # Add name here from current checkpoint info
                "sequence_order": curr.get("sequence_order", -1),
                "current_segment": curr["segment_time"],
                "ghost_segment": gh["segment_time"],
                "segment_delta": seg_delta,
                "current_cumulative": curr["cumulative_time"],
                "ghost_cumulative": gh["cumulative_time"],
                "cumulative_delta": cum_delta
            })
        return pd.DataFrame(comparison)

    def get_pb_ghost_comparison(self, run_id):
        run = self.get_run_details(run_id)
        if not run:
            return None
        pb = self.get_personal_best(run["route_id"])
        if not pb or pb['run_id'] == run_id:
            return None
        return self.get_ghost_comparison(run_id, pb['run_id'])

    def get_live_ghost_data(self, route_id):
        pb = self.get_personal_best(route_id)
        if not pb:
            return None
        return self.get_run_checkpoint_times(pb['run_id'])
