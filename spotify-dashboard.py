import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import json

# Page configuration
st.set_page_config(
    page_title="eBike Dashboard",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #00ff00;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #00ff00;
        margin: 0.5rem 0;
    }
    .spotify-player {
        background-color: #1DB954;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .navigation-panel {
        background-color: #2d2d2d;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class EBikeDashboard:
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        if 'battery_level' not in st.session_state:
            st.session_state.battery_level = 100
        if 'speed' not in st.session_state:
            st.session_state.speed = 0
        if 'distance' not in st.session_state:
            st.session_state.distance = 0
        if 'assist_level' not in st.session_state:
            st.session_state.assist_level = 1
        if 'is_riding' not in st.session_state:
            st.session_state.is_riding = False
        if 'current_song' not in st.session_state:
            st.session_state.current_song = "Not Playing"
        if 'destination' not in st.session_state:
            st.session_state.destination = ""
        if 'eta' not in st.session_state:
            st.session_state.eta = "00:00"

    def display_header(self):
        st.markdown('<h1 class="main-header">🚴 eBike Smart Dashboard</h1>', unsafe_allow_html=True)
    
    def display_metrics(self):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🔋 Battery</h3>
                <h2>{st.session_state.battery_level}%</h2>
                <progress value="{st.session_state.battery_level}" max="100"></progress>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>⚡ Speed</h3>
                <h2>{st.session_state.speed} km/h</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📏 Distance</h3>
                <h2>{st.session_state.distance:.1f} km</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🔄 Assist Level</h3>
                <h2>{st.session_state.assist_level}/5</h2>
            </div>
            """, unsafe_allow_html=True)
    
    def display_spotify_player(self):
        st.markdown("""
        <div class="spotify-player">
            <h2>🎵 Spotify Player</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Spotify Web Player Integration
        st.markdown("""
        <iframe src="https://open.spotify.com/embed/playlist/37i9dQZF1DXcBWIGoYBM5M" 
                width="100%" height="380" frameborder="0" allowtransparency="true" 
                allow="encrypted-media"></iframe>
        """, unsafe_allow_html=True)
        
        # Current playing display
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text_input("Now Playing", value=st.session_state.current_song, disabled=True)
        with col2:
            if st.button("🎵 Play/Pause"):
                self.toggle_music()
        
        # Quick playlists
        st.subheader("Quick Playlists")
        playlist_cols = st.columns(4)
        playlists = {
            "🚴 Cycling Mix": "37i9dQZF1DX4WYpdgoIcn6",
            "🏞️ Nature Sounds": "37i9dQZF1DX4Um6aTshYxP",
            "🎶 Energy Boost": "37i9dQZF1DX0vHZ8elq0UK",
            "🛣️ Road Trip": "37i9dQZF1DX4WYpdgoIcn6"
        }
        
        for col, (name, playlist_id) in zip(playlist_cols, playlists.items()):
            with col:
                if st.button(name):
                    st.session_state.current_song = f"Playing {name}"
                    st.rerun()
    
    def toggle_music(self):
        if st.session_state.current_song == "Not Playing":
            st.session_state.current_song = "Playing - Electric Feel by MGMT"
        else:
            st.session_state.current_song = "Not Playing"
    
    def display_navigation(self):
        st.markdown("""
        <div class="navigation-panel">
            <h2>🧭 Navigation</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            destination = st.text_input("Enter Destination", value=st.session_state.destination)
            if destination != st.session_state.destination:
                st.session_state.destination = destination
                if destination:
                    # Simulate route calculation
                    st.session_state.eta = "25:15"
        
        with col2:
            st.text_input("ETA", value=st.session_state.eta, disabled=True)
        
        # Map display (simplified)
        st.subheader("Route Overview")
        
        # Create a simple map visualization
        map_data = pd.DataFrame({
            'lat': [51.5074, 51.5174, 51.5274, 51.5374],
            'lon': [-0.1278, -0.1178, -0.1078, -0.0978]
        })
        st.map(map_data, zoom=12)
        
        # Turn-by-turn directions
        st.subheader("Turn-by-Turn Directions")
        directions = [
            "Head north on Main St (0.2 km)",
            "Turn right onto Oak Ave (1.5 km)",
            "Continue straight onto Park Rd (3.2 km)",
            "Destination on your left"
        ]
        
        for i, direction in enumerate(directions, 1):
            st.write(f"{i}. {direction}")
    
    def display_controls(self):
        st.sidebar.header("eBike Controls")
        
        # Power control
        if st.sidebar.button("🚦 Start/Stop Ride"):
            st.session_state.is_riding = not st.session_state.is_riding
            if st.session_state.is_riding:
                self.start_ride()
            else:
                self.stop_ride()
        
        # Assist level control
        st.sidebar.subheader("Pedal Assist Level")
        new_level = st.sidebar.slider("", 1, 5, st.session_state.assist_level)
        if new_level != st.session_state.assist_level:
            st.session_state.assist_level = new_level
        
        # Battery management
        st.sidebar.subheader("Battery Management")
        st.sidebar.progress(st.session_state.battery_level / 100)
        
        if st.sidebar.button("🔋 Simulate Battery Drain"):
            self.simulate_battery_drain()
        
        if st.sidebar.button("🔌 Simulate Charge"):
            self.simulate_charge()
        
        # Ride statistics
        st.sidebar.subheader("Ride Statistics")
        st.sidebar.metric("Total Distance", f"{st.session_state.distance:.1f} km")
        st.sidebar.metric("Average Speed", f"{st.session_state.speed:.1f} km/h")
        st.sidebar.metric("CO2 Saved", f"{(st.session_state.distance * 0.2):.1f} kg")
    
    def simulate_battery_drain(self):
        if st.session_state.battery_level > 0:
            st.session_state.battery_level -= 5
            if st.session_state.battery_level < 0:
                st.session_state.battery_level = 0
    
    def simulate_charge(self):
        if st.session_state.battery_level < 100:
            st.session_state.battery_level += 20
            if st.session_state.battery_level > 100:
                st.session_state.battery_level = 100
    
    def start_ride(self):
        st.session_state.is_riding = True
        st.session_state.speed = 15  # Starting speed
    
    def stop_ride(self):
        st.session_state.is_riding = False
        st.session_state.speed = 0
    
    def update_ride_data(self):
        if st.session_state.is_riding:
            # Simulate riding data changes
            st.session_state.speed = max(0, min(30, st.session_state.speed + np.random.uniform(-2, 2)))
            st.session_state.distance += st.session_state.speed / 3600  # km per second
            
            # Battery drains faster at higher speeds and assist levels
            battery_drain = (st.session_state.speed * st.session_state.assist_level) / 10000
            st.session_state.battery_level = max(0, st.session_state.battery_level - battery_drain)
    
    def display_weather(self):
        st.sidebar.subheader("🌤️ Weather Conditions")
        weather_data = {
            "Temperature": "18°C",
            "Conditions": "Partly Cloudy",
            "Wind": "12 km/h",
            "Humidity": "65%"
        }
        
        for key, value in weather_data.items():
            st.sidebar.text(f"{key}: {value}")
    
    def run(self):
        self.display_header()
        self.display_metrics()
        
        # Main content area
        tab1, tab2, tab3 = st.tabs(["🎵 Music", "🧭 Navigation", "📊 Statistics"])
        
        with tab1:
            self.display_spotify_player()
        
        with tab2:
            self.display_navigation()
        
        with tab3:
            self.display_statistics()
        
        # Sidebar controls
        self.display_controls()
        self.display_weather()
        
        # Auto-update ride data
        self.update_ride_data()
        
        # Auto-refresh every 5 seconds
        time.sleep(5)
        st.rerun()
    
    def display_statistics(self):
        st.subheader("📊 Ride Statistics")
        
        # Generate sample ride data
        dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
        ride_data = pd.DataFrame({
            'Date': dates,
            'Distance': np.random.uniform(5, 25, len(dates)),
            'Average Speed': np.random.uniform(12, 22, len(dates)),
            'Calories Burned': np.random.uniform(150, 400, len(dates))
        })
        
        # Display charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.line_chart(ride_data.set_index('Date')['Distance'])
            st.write("Daily Distance (km)")
        
        with col2:
            st.line_chart(ride_data.set_index('Date')['Average Speed'])
            st.write("Average Speed (km/h)")
        
        # Monthly summary
        st.subheader("Monthly Summary")
        summary_cols = st.columns(3)
        with summary_cols[0]:
            st.metric("Total Distance", f"{ride_data['Distance'].sum():.1f} km")
        with summary_cols[1]:
            st.metric("Total Rides", len(ride_data))
        with summary_cols[2]:
            st.metric("CO2 Saved", f"{(ride_data['Distance'].sum() * 0.2):.1f} kg")

# Run the dashboard
if __name__ == "__main__":
    dashboard = EBikeDashboard()
    dashboard.run()
