# Create the main Streamlit application
streamlit_app_code = '''
import streamlit as st
import time
from datetime import datetime, timedelta
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
if 'run_start_time' not in st.session_state:
    st.session_state.run_start_time = None
if 'last_checkpoint_time' not in st.session_state:
    st.session_state.last_checkpoint_time = None
if 'current_checkpoint_index' not in st.session_state:
    st.session_state.current_checkpoint_index = 0
if 'checkpoints_data' not in st.session_state:
    st.session_state.checkpoints_data = []

def format_time(seconds):
    """Format seconds into MM:SS.ms format"""
    if seconds is None:
        return "--:--"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:06.3f}"

def start_new_run(route_id, notes=""):
    """Initialize a new run"""
    run_id = db.start_run(route_id, notes)
    st.session_state.active_run = run_id
    st.session_state.run_start_time = time.time()
    st.session_state.last_checkpoint_time = time.time()
    st.session_state.current_checkpoint_index = 0
    st.session_state.checkpoints_data = db.get_checkpoints(route_id)
    return run_id

def record_checkpoint():
    """Record checkpoint time"""
    current_time = time.time()
    segment_time = current_time - st.session_state.last_checkpoint_time
    
    checkpoint = st.session_state.checkpoints_data[st.session_state.current_checkpoint_index]
    db.record_checkpoint_time(st.session_state.active_run, checkpoint['id'], segment_time)
    
    st.session_state.last_checkpoint_time = current_time
    st.session_state.current_checkpoint_index += 1
    
    # Check if this was the last checkpoint
    if st.session_state.current_checkpoint_index >= len(st.session_state.checkpoints_data):
        total_time = current_time - st.session_state.run_start_time
        db.complete_run(st.session_state.active_run, total_time)
        return True, total_time
    return False, None

def cancel_run():
    """Cancel the current run"""
    st.session_state.active_run = None
    st.session_state.run_start_time = None
    st.session_state.last_checkpoint_time = None
    st.session_state.current_checkpoint_index = 0
    st.session_state.checkpoints_data = []

# Main app
st.title("🏁 Time Attack Tracker")
st.markdown("---")

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["🏁 Active Run", "🛣️ Manage Routes", "📊 Analytics Dashboard"])

# ==================== ACTIVE RUN PAGE ====================
if page == "🏁 Active Run":
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
        
        current_time = time.time()
        elapsed = current_time - st.session_state.run_start_time
        segment_elapsed = current_time - st.session_state.last_checkpoint_time
        
        # Real-time timer display
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Time", format_time(elapsed))
        with col2:
            st.metric("Segment Time", format_time(segment_elapsed))
        with col3:
            checkpoint_progress = f"{st.session_state.current_checkpoint_index}/{len(st.session_state.checkpoints_data)}"
            st.metric("Checkpoints", checkpoint_progress)
        
        # Current checkpoint info
        if st.session_state.current_checkpoint_index < len(st.session_state.checkpoints_data):
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
        
        # Auto-refresh for real-time timer
        time.sleep(0.1)
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
                st.metric("Date", pb['date'].split()[0])
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
            
            # Run history table
            st.write("**Recent Runs:**")
            display_df = history[['start_time', 'total_time_seconds', 'notes']].copy()
            display_df['total_time_seconds'] = display_df['total_time_seconds'].apply(format_time)
            display_df.columns = ['Date/Time', 'Time', 'Notes']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
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

st.sidebar.markdown("---")
st.sidebar.caption("Time Attack Tracker v1.0")
'''

# Save Streamlit app
with open('app.py', 'w') as f:
    f.write(streamlit_app_code)

print("✓ Created app.py (Main Streamlit Application)")
