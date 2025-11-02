# Create requirements.txt file
requirements = '''streamlit==1.39.0
pandas==2.2.3
plotly==5.24.1
'''

with open('requirements.txt', 'w') as f:
    f.write(requirements)

print("✓ Created requirements.txt")

# Create README with instructions
readme = '''# Time Attack Tracker 🏁

A Streamlit-based application for tracking your daily commute time like a racing game time attack mode.

## Features

- ⏱️ **Manual Checkpoint Tracking**: Press buttons to mark when you reach each checkpoint
- 🏆 **Personal Bests**: Track your fastest times for each route
- 📊 **Analytics Dashboard**: View trends, statistics, and checkpoint performance
- 🛣️ **Multiple Routes**: Create and manage different routes (home to office, office to home, etc.)
- 💾 **SQLite Database**: All data stored locally in a lightweight database

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## How to Use

### 1. Create a Route

- Go to **"Manage Routes"** page
- Click on **"Create New Route"** tab
- Enter route name (e.g., "Home to Office")
- Add description (optional)
- Define checkpoints (e.g., "Start", "Highway Entrance", "Office Exit", "Office Parking")
- Click **"Create Route"**

### 2. Start a Run

- Go to **"Active Run"** page
- Select your route from dropdown
- Add optional notes (e.g., "Heavy traffic", "Clear roads")
- Click **"Start Run"** button

### 3. Record Checkpoint Times

- As you reach each checkpoint during your commute, press **"Checkpoint Reached"** button
- The app will automatically:
  - Record the segment time
  - Move to the next checkpoint
  - Update your total time
- Continue until you reach the final checkpoint (finish line)

### 4. View Analytics

- Go to **"Analytics Dashboard"** page
- Select a route to analyze
- View:
  - Personal best time
  - Run history graph
  - Statistics (average, fastest, slowest)
  - Checkpoint performance analysis
  - Which segments are slowest/fastest

## Tips

- **Mounting your phone**: Use a phone holder in your car for easy button access
- **Safety first**: Only press buttons when safely stopped or have a passenger help
- **Consistency**: Try to press checkpoint buttons at the same physical location each time
- **Notes**: Add notes about traffic, weather, or route changes to understand time variations

## Database

The application uses SQLite database (`time_attack.db`) which will be created automatically on first run. All your data is stored locally.

## File Structure

```
time_attack_tracker/
├── app.py              # Main Streamlit application
├── init_db.py          # Database initialization
├── db_helpers.py       # Database helper functions
├── requirements.txt    # Python dependencies
├── time_attack.db      # SQLite database (created on first run)
└── README.md           # This file
```

## Future Enhancements (Not Implemented Yet)

- GPS-based automatic checkpoint detection
- Export data to CSV/JSON
- Multi-user support
- Pause/resume functionality
- Weather API integration
- Ghost comparison (real-time delta vs personal best)

---

**Version**: 1.0  
**Built with**: Streamlit, SQLite, Pandas, Plotly
'''

with open('README.md', 'w') as f:
    f.write(readme)

print("✓ Created README.md")
print("\n" + "="*60)
print("APPLICATION CREATED SUCCESSFULLY! 🎉")
print("="*60)
print("\nFiles created:")
print("  1. app.py - Main Streamlit application")
print("  2. init_db.py - Database initialization")
print("  3. db_helpers.py - Database helper functions")
print("  4. requirements.txt - Python dependencies")
print("  5. README.md - Documentation")
print("\nTo run the application:")
print("  1. Install dependencies: pip install -r requirements.txt")
print("  2. Run the app: streamlit run app.py")
print("="*60)
