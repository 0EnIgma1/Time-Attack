import streamlit as st
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from init_db import init_db
from db_helpers import TimeAttackDB

# Initialize database on first run
init_db()
db = TimeAttackDB()

# Configure page
st.set_page_config(page_title="Time Attack Tracker", page_icon="🏁", layout="wide")

# Initialize session state
if 'active_run' not in st.session_state:
    st.session_state.active_run = None
if 'current_checkpoint_index' not in st.session_state:
    st.session_state.current_checkpoint_index = 0
if 'checkpoints_data' not in st.session_state:
    st.session_state.checkpoints_data = []
if 'ghost_data' not in st.session_state:
    st.session_state.ghost_data = None

def format_time(seconds):
    if seconds is None or pd.isna(seconds):
        return "--:--"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:06.3f}"

def format_delta(seconds):
    """Format delta time with +/- sign"""
    if seconds is None:
        return "--"
    sign = "+" if seconds > 0 else ""
    return f"{sign}{seconds:.3f}s"

def format_delta_minutes(seconds):
    """Format delta time in minutes with +/- sign"""
    if seconds is None:
        return "--"
    sign = "+" if seconds > 0 else ""
    minutes = seconds / 60.0
    return f"{sign}{minutes:.2f} mins"

def start_new_run(route_id, notes=""):
    """Initialize a new run and store start_time in db"""
    run_id = db.start_run(route_id, notes)
    st.session_state.active_run = run_id
    st.session_state.current_checkpoint_index = 0
    st.session_state.checkpoints_data = db.get_checkpoints(route_id)
    st.session_state.ghost_data = db.get_live_ghost_data(route_id)
    return run_id

def record_checkpoint():
    run_id = st.session_state.active_run
    cp_idx = st.session_state.current_checkpoint_index
    all_cps = st.session_state.checkpoints_data

    run_details = db.get_run_details(run_id)
    prev_cp_times = db.get_run_checkpoint_times(run_id)
    
    # Get last event time
    if cp_idx == 0:
        last_time = datetime.fromisoformat(run_details['start_time'].replace("Z", "+00:00"))
    else:
        last_time = datetime.fromisoformat(str(prev_cp_times[-1]['time_reached']).replace("Z", "+00:00"))

    now = datetime.now(timezone.utc)
    segment_time = (now - last_time).total_seconds()

    checkpoint = all_cps[cp_idx]
    db.record_checkpoint_time(run_id, checkpoint['id'], segment_time)
    st.session_state.current_checkpoint_index += 1

    # If last checkpoint, complete run and write total time
    if st.session_state.current_checkpoint_index >= len(all_cps):
        run_start = datetime.fromisoformat(run_details['start_time'].replace("Z", "+00:00"))
        total_time = (now - run_start).total_seconds()
        db.complete_run(run_id, total_time)

        # Reset active run state and rerun UI
        cancel_run()
        st.rerun()
        return True, total_time

    return False, None

def cancel_run():
    """Cancel the current run"""
    st.session_state.active_run = None
    st.session_state.current_checkpoint_index = 0
    st.session_state.checkpoints_data = []
    st.session_state.ghost_data = None


# Main app
st.title("🏁 GRID - Time Attack")
st.markdown("---")

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["🏁 Active Run", "🛣️ Manage Routes", "📊 Analytics Dashboard", "👻 Run Analysis"])

# ==================== ACTIVE RUN PAGE ====================
if page == "🏁 Active Run":

    # On first load/after disconnect:
    if st.session_state.active_run is None:
        latest = db.get_latest_active_run()
        if latest:
            st.session_state.active_run = latest['id']
            st.session_state.checkpoints_data = db.get_checkpoints(latest['route_id'])
            cptimes = db.get_run_checkpoint_times(latest['id'])
            st.session_state.current_checkpoint_index = len(cptimes)
            st.session_state.ghost_data = db.get_live_ghost_data(latest['route_id'])

    if st.session_state.active_run is None:
        st.header("Start New Run")
        routes = db.get_routes()
        if not routes:
            st.warning("⚠️ No routes configured. Please create a route first in 'Manage Routes'.")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                route_options = {r['name']: r['id'] for r in routes}
                selected_route_name = st.selectbox("Select Route", list(route_options.keys()))
                selected_route_id = route_options[selected_route_name]
                notes = st.text_input("Notes (optional)", placeholder="e.g., Heavy traffic, rainy weather")
            with col2:
                st.write("")
                st.write("")
                if st.button("🚀 Start Run", type="primary", use_container_width=True):
                    checkpoints = db.get_checkpoints(selected_route_id)
                    if not checkpoints:
                        st.error("❌ This route has no checkpoints. Please add checkpoints first.")
                    else:
                        start_new_run(selected_route_id, notes)
                        st.rerun()
    else:
        # Active run interface
        st.header("⏱️ Run in Progress")

        run_details = db.get_run_details(st.session_state.active_run)
        prev_cp_times = db.get_run_checkpoint_times(st.session_state.active_run)

        now = datetime.now(timezone.utc)
        # Calculate total elapsed time based on start_time in db:
        elapsed = (now - datetime.fromisoformat(run_details['start_time'].replace("Z", "+00:00"))).total_seconds()

        # Last event time:
        if st.session_state.current_checkpoint_index == 0:
            last_time = datetime.fromisoformat(run_details['start_time'].replace("Z", "+00:00"))
        else:
            last_time = datetime.fromisoformat(str(prev_cp_times[-1]['time_reached']).replace("Z", "+00:00"))
        segment_elapsed = (now - last_time).total_seconds()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Time", format_time(elapsed))
        with col2:
            st.metric("Segment Time", format_time(segment_elapsed))
        with col3:
            checkpoint_progress = f"{st.session_state.current_checkpoint_index}/{len(st.session_state.checkpoints_data)}"
            st.metric("Checkpoints", checkpoint_progress)

        # Ghost comparison during run
        if st.session_state.ghost_data and st.session_state.current_checkpoint_index > 0:
            st.markdown("---")
            st.subheader("👻 Ghost Comparison (vs Personal Best)")
            ghost_cumulative = 0
            for i in range(st.session_state.current_checkpoint_index):
                if i < len(st.session_state.ghost_data):
                    ghost_cumulative = st.session_state.ghost_data[i]['cumulative_time']
            delta = elapsed - ghost_cumulative
            delta_color = "red" if delta > 0 else "green"
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Your Cumulative Time", format_time(elapsed))
            with c2:
                st.metric("Ghost Cumulative Time", format_time(ghost_cumulative))
            with c3:
                st.metric("Delta", format_delta(delta))
                if delta > 0:
                    st.markdown(f":{delta_color}[Behind ghost by {abs(delta):.3f}s]")
                else:
                    st.markdown(f":{delta_color}[Ahead of ghost by {abs(delta):.3f}s!]")

        # Current checkpoint info
        if st.session_state.current_checkpoint_index < len(st.session_state.checkpoints_data):
            st.markdown("---")
            current_checkpoint = st.session_state.checkpoints_data[st.session_state.current_checkpoint_index]
            st.subheader(f"🎯 Next Checkpoint: {current_checkpoint['name']}")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("✅ Checkpoint Reached", type="primary", use_container_width=True):
                    is_finished, total_time = record_checkpoint()
                    if is_finished:
                        st.success(f"🏁 Run Complete! Total Time: {format_time(total_time)}")
                        time.sleep(2)
                        cancel_run()
                        st.rerun()
                    else:
                        st.rerun()
            with col2:
                if st.button("❌ Cancel Run", use_container_width=True):
                    cancel_run()
                    st.rerun()

# ==================== MANAGE ROUTES PAGE ====================
elif page == "🛣️ Manage Routes":
    st.header("Route Management")

    tab1, tab2 = st.tabs(["📋 View Routes", "➕ Create New Route"])

    with tab1:
        routes = db.get_routes()
        if not routes:
            st.info("No routes created yet. Create your first route in the 'Create New Route' tab!")
        else:
            for route in routes:
                with st.expander(f"🛣️ {route['name']}", expanded=False):
                    st.write(f"**Description:** {route['description'] or 'No description'}")
                    st.write(f"**Created:** {route['created_at']}")

                    checkpoints = db.get_checkpoints(route['id'])
                    if checkpoints:
                        st.write("**Checkpoints:**")
                        for cp in checkpoints:
                            st.write(f"  {cp['sequence_order']}. {cp['name']}")
                    else:
                        st.warning("No checkpoints configured for this route.")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Edit Checkpoints", key=f"edit_{route['id']}"):
                            st.session_state.editing_route = route['id']
                    with col2:
                        if st.button(f"🗑️ Delete Route", key=f"del_{route['id']}"):
                            db.delete_route(route['id'])
                            st.success(f"Deleted route: {route['name']}")
                            st.rerun()

                    # Checkpoint editing section
                    if 'editing_route' in st.session_state and st.session_state.editing_route == route['id']:
                        st.write("---")
                        st.subheader("Add Checkpoint")
                        cp_name = st.text_input(f"Checkpoint Name", key=f"cp_name_{route['id']}")
                        if checkpoints:
                            next_order = max([cp['sequence_order'] for cp in checkpoints]) + 1
                        else:
                            next_order = 1

                        if st.button(f"Add Checkpoint", key=f"add_cp_{route['id']}"):
                            if cp_name:
                                db.add_checkpoint(route['id'], cp_name, next_order)
                                st.success(f"Added checkpoint: {cp_name}")
                                st.rerun()

    with tab2:
        st.subheader("Create New Route")
        route_name = st.text_input("Route Name", placeholder="e.g., Home to Office")
        route_desc = st.text_area("Description", placeholder="e.g., Via highway, usual morning route")

        st.write("**Checkpoints:**")
        num_checkpoints = st.number_input("Number of Checkpoints", min_value=1, max_value=20, value=3)

        checkpoint_names = []
        for i in range(num_checkpoints):
            cp_name = st.text_input(f"Checkpoint {i+1}", key=f"new_cp_{i}", placeholder=f"e.g., Highway entrance")
            checkpoint_names.append(cp_name)

        if st.button("Create Route", type="primary"):
            if not route_name:
                st.error("Please enter a route name")
            elif not all(checkpoint_names):
                st.error("Please fill in all checkpoint names")
            else:
                try:
                    route_id = db.create_route(route_name, route_desc)
                    for idx, cp_name in enumerate(checkpoint_names, 1):
                        db.add_checkpoint(route_id, cp_name, idx)
                    st.success(f"✅ Route '{route_name}' created successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating route: {str(e)}")

# ==================== ANALYTICS DASHBOARD ====================
elif page == "📊 Analytics Dashboard":
    st.header("Analytics Dashboard")

    routes = db.get_routes()
    if not routes:
        st.warning("No routes available for analysis.")
    else:
        route_options = {r['name']: r['id'] for r in routes}
        selected_route_name = st.selectbox("Select Route for Analysis", list(route_options.keys()))
        selected_route_id = route_options[selected_route_name]

        # Personal Best
        st.subheader("🏆 Personal Best")
        pb = db.get_personal_best(selected_route_id)
        if pb:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Best Time", format_time(pb['time_seconds']))
            with col2:
                st.metric("Date", pb['date'].split("T")[0])
        else:
            st.info("No completed runs yet.")

        # Run History
        st.subheader("📈 Run History")
        history = db.get_run_history(selected_route_id)

        if not history.empty:
            # Time trend chart
            fig = px.line(history, x='start_time', y='total_time_seconds', 
                         title='Time Progression Over Runs',
                         labels={'start_time': 'Date', 'total_time_seconds': 'Time (seconds)'})
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

            # Statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Runs", len(history))
            with col2:
                st.metric("Average Time", format_time(history['total_time_seconds'].mean()))
            with col3:
                st.metric("Fastest", format_time(history['total_time_seconds'].min()))
            with col4:
                st.metric("Slowest", format_time(history['total_time_seconds'].max()))

            # Run history table with pagination
            st.subheader("Recent Runs")

            # Format the dataframe for display
            display_history = history.copy()

            # Parse datetime and format columns
            display_history['date_obj'] = pd.to_datetime(display_history['start_time'])
            display_history = display_history.sort_values('date_obj', ascending=False)

            # Format display columns
            display_history['Date'] = display_history['date_obj'].dt.strftime('%d/%m/%Y')
            display_history['Time'] = display_history['date_obj'].dt.strftime('%H:%M:%S')
            display_history['Day'] = display_history['date_obj'].dt.strftime('%A')
            display_history['Duration'] = display_history['total_time_seconds'].apply(format_time)
            display_history['Notes'] = display_history['notes'].fillna('-')

            # Select columns for display
            final_display = display_history[['Date', 'Day', 'Time', 'Duration', 'Notes']].reset_index(drop=True)

            # Pagination controls
            rows_per_page = st.selectbox("Rows per page", [10, 25, 50, 100], index=0)
            total_rows = len(final_display)
            total_pages = (total_rows - 1) // rows_per_page + 1

            if 'current_page' not in st.session_state:
                st.session_state.current_page = 1

            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if st.button("⬅️ Previous", disabled=(st.session_state.current_page <= 1)):
                    st.session_state.current_page -= 1
                    st.rerun()

            with col2:
                st.markdown(f"<h4 style='text-align: center;'>Page {st.session_state.current_page} of {total_pages}</h4>", 
                           unsafe_allow_html=True)

            with col3:
                if st.button("Next ➡️", disabled=(st.session_state.current_page >= total_pages)):
                    st.session_state.current_page += 1
                    st.rerun()

            # Calculate start and end indices for current page
            start_idx = (st.session_state.current_page - 1) * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_rows)

            # Display paginated data
            page_data = final_display.iloc[start_idx:end_idx]
            st.dataframe(page_data, use_container_width=True, hide_index=True)

            st.caption(f"Showing {start_idx + 1}-{end_idx} of {total_rows} runs")

            # Checkpoint Analysis
            st.subheader("🎯 Checkpoint Performance")
            cp_analysis = db.get_checkpoint_analysis(selected_route_id)
            if not cp_analysis.empty:
                cp_analysis['avg_time'] = cp_analysis['avg_time'].apply(format_time)
                cp_analysis['best_time'] = cp_analysis['best_time'].apply(format_time)
                cp_analysis['worst_time'] = cp_analysis['worst_time'].apply(format_time)
                cp_analysis.columns = ['Checkpoint', 'Order', 'Avg Time', 'Best Time', 'Worst Time', 'Completed']
                st.dataframe(cp_analysis, use_container_width=True, hide_index=True)
        else:
            st.info("No completed runs for this route yet.")

# ==================== RUN ANALYSIS PAGE ====================
elif page == "👻 Run Analysis":
    st.header("👻 Individual Run Analysis with Ghost Comparison")

    routes = db.get_routes()
    if not routes:
        st.warning("No routes available for analysis.")
    else:
        route_options = {r['name']: r['id'] for r in routes}
        selected_route_name = st.selectbox("Select Route", list(route_options.keys()))
        selected_route_id = route_options[selected_route_name]

        # Get run history
        history = db.get_run_history(selected_route_id)

        if history.empty:
            st.info("No completed runs for this route yet.")
        else:
            # Create run selector
            run_options = {}
            for idx, row in history.iterrows():
                # Parse the datetime string
                dt = datetime.fromisoformat(row['start_time'].replace("Z", "+00:00"))

                # Format: DD/MM/YYYY - Day - Total time
                date_str = dt.strftime("%d/%m/%Y")
                day_str = dt.strftime("%A")
                time_str = format_time(row['total_time_seconds'])

                run_label = f"{date_str} - {day_str} - {time_str}"

                # Add notes if available
                if row['notes']:
                    run_label += f" ({row['notes']})"

                run_options[run_label] = row['id']

            selected_run_label = st.selectbox("Select Run to Analyze", list(run_options.keys()))
            selected_run_id = run_options[selected_run_label]

            # Get run details
            run_details = db.get_run_details(selected_run_id)
            pb = db.get_personal_best(selected_route_id)

            if run_details:
                st.markdown("---")

                # Run Summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Time", format_time(run_details['total_time_seconds']))
                with col2:
                    if pb and run_details['id'] == pb['run_id']:
                        st.metric("Status", "🏆 Personal Best!")
                    else:
                        st.metric("Status", "Completed")
                with col3:
                    st.metric("Date", run_details['start_time'].split("T")[0])

                if run_details['notes']:
                    st.info(f"**Notes:** {run_details['notes']}")

                # Delete button
                st.markdown("---")
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    if st.button("🗑️ Delete This Run", type="secondary", use_container_width=True):
                        db.delete_run(selected_run_id)
                        st.success(f"Run deleted successfully!")
                        time.sleep(1)
                        st.rerun()

                # Ghost Comparison
                st.markdown("---")
                st.subheader("👻 Ghost Comparison vs Personal Best")

                ghost_comparison = db.get_pb_ghost_comparison(selected_run_id)

                if ghost_comparison is not None and not ghost_comparison.empty:
                    # Format the comparison data
                    display_comp = ghost_comparison.copy()
                    display_comp['current_segment'] = display_comp['current_segment'].apply(format_time)
                    display_comp['ghost_segment'] = display_comp['ghost_segment'].apply(format_time)
                    display_comp['segment_delta_sec'] = display_comp['segment_delta'].apply(format_delta)
                    display_comp['segment_delta_mins'] = display_comp['segment_delta'].apply(format_delta_minutes)
                    display_comp['segment_delta_combined'] = display_comp.apply(
                        lambda row: f"{row['segment_delta_sec']} ({row['segment_delta_mins']})", axis=1
                    )
                    display_comp['current_cumulative'] = display_comp['current_cumulative'].apply(format_time)
                    display_comp['ghost_cumulative'] = display_comp['ghost_cumulative'].apply(format_time)
                    display_comp['cumulative_delta'] = display_comp['cumulative_delta'].apply(format_delta)

                    display_comp_show = display_comp[['checkpoint_name', 'sequence_order', 'current_segment', 
                                      'ghost_segment', 'segment_delta_combined', 
                                      'current_cumulative', 'ghost_cumulative', 'cumulative_delta']].copy()
                    display_comp_show.columns = ['Checkpoint', 'Order', 'Your Segment', 'Ghost Segment', 'Segment Δ', 
                                        'Your Cumulative', 'Ghost Cumulative', 'Cumulative Δ']

                    st.dataframe(display_comp_show, use_container_width=True, hide_index=True)

                    # Visualize delta progression
                    st.subheader("📊 Delta Progression")
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=ghost_comparison['checkpoint_name'],
                        y=ghost_comparison['cumulative_delta'],
                        mode='lines+markers',
                        name='Cumulative Delta',
                        line=dict(color='blue', width=3),
                        marker=dict(size=10)
                    ))

                    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Even with Ghost")

                    fig.update_layout(
                        title="Time Delta vs Personal Best (Negative = Faster)",
                        xaxis_title="Checkpoint",
                        yaxis_title="Delta (seconds)",
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Segment-by-segment comparison chart
                    st.subheader("🎯 Segment Time Comparison")
                    fig2 = go.Figure()

                    fig2.add_trace(go.Bar(
                        x=ghost_comparison['checkpoint_name'],
                        y=ghost_comparison['current_segment'],
                        name='Your Time',
                        marker_color='lightblue'
                    ))

                    fig2.add_trace(go.Bar(
                        x=ghost_comparison['checkpoint_name'],
                        y=ghost_comparison['ghost_segment'],
                        name='Ghost (PB) Time',
                        marker_color='lightgreen'
                    ))

                    fig2.update_layout(
                        title="Segment Times: You vs Ghost",
                        xaxis_title="Checkpoint",
                        yaxis_title="Time (seconds)",
                        barmode='group'
                    )

                    st.plotly_chart(fig2, use_container_width=True)

                    # Summary insights
                    st.markdown("---")
                    st.subheader("💡 Insights")

                    # Find best and worst segments
                    best_segment_idx = ghost_comparison['segment_delta'].idxmin()
                    worst_segment_idx = ghost_comparison['segment_delta'].idxmax()

                    best_segment = ghost_comparison.loc[best_segment_idx]
                    worst_segment = ghost_comparison.loc[worst_segment_idx]

                    col1, col2 = st.columns(2)
                    with col1:
                        st.success(f"**Best Segment:** {best_segment['checkpoint_name']}")
                        st.write(f"Faster by {abs(best_segment['segment_delta']):.3f}s vs ghost")

                    with col2:
                        st.error(f"**Worst Segment:** {worst_segment['checkpoint_name']}")
                        st.write(f"Slower by {worst_segment['segment_delta']:.3f}s vs ghost")

                    # Final delta
                    final_delta = ghost_comparison.iloc[-1]['cumulative_delta']
                    if final_delta < 0:
                        st.success(f"🏆 You finished **{abs(final_delta):.3f}s faster** than your personal best ghost!")
                    else:
                        st.info(f"You finished **{final_delta:.3f}s slower** than your personal best. Keep pushing!")

                elif pb and run_details['id'] == pb['run_id']:
                    st.info("🏆 This IS your personal best! No ghost to compare against.")
                else:
                    st.warning("No personal best available for comparison yet.")

st.sidebar.markdown("---")
st.sidebar.caption("Time Attack Tracker v1.0 with Ghost Mode")
