import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import requests
import json
import base64
import os
from typing import Dict, List, Optional
import polyline

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
    .turn-instruction {
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        background-color: #3a3a3a;
        border-left: 4px solid #00ff00;
    }
    .current-step {
        background-color: #1e3a1e;
        border-left: 4px solid #00ff00;
    }
</style>
""", unsafe_allow_html=True)

class SpotifyAPI:
    def __init__(self):
        self.client_id = st.secrets.get("SPOTIFY_CLIENT_ID", "")
        self.client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET", "")
        self.redirect_uri = "http://localhost:8501"
        self.access_token = None
        self.refresh_token = None
        
    def get_auth_url(self):
        scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing streaming"
        auth_url = f"https://accounts.spotify.com/authorize?response_type=code&client_id={self.client_id}&scope={scope}&redirect_uri={self.redirect_uri}"
        return auth_url
        
    def get_tokens(self, code):
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            return True
        return False
        
    def refresh_access_token(self):
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens['access_token']
            return True
        return False
        
    def make_request(self, endpoint, method='GET', data=None):
        if not self.access_token:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://api.spotify.com/v1{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
                
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                if self.refresh_access_token():
                    return self.make_request(endpoint, method, data)
            return None
        except Exception as e:
            st.error(f"Spotify API error: {e}")
            return None
            
    def get_current_playback(self):
        return self.make_request('/me/player')
        
    def play_track(self, track_uri=None, context_uri=None):
        data = {}
        if track_uri:
            data['uris'] = [track_uri]
        elif context_uri:
            data['context_uri'] = context_uri
            
        return self.make_request('/me/player/play', method='PUT', data=data)
        
    def pause_playback(self):
        return self.make_request('/me/player/pause', method='PUT')
        
    def next_track(self):
        return self.make_request('/me/player/next', method='POST')
        
    def previous_track(self):
        return self.make_request('/me/player/previous', method='POST')
        
    def search_tracks(self, query, limit=10):
        endpoint = f"/search?q={query}&type=track&limit={limit}"
        return self.make_request(endpoint)

class NavigationAPI:
    def __init__(self):
        self.provider = st.secrets.get("NAVIGATION_PROVIDER", "openstreetmap")
        self.api_key = st.secrets.get("NAVIGATION_API_KEY", "")
        
    def get_route(self, start_lng, start_lat, end_lng, end_lat):
        """Get route using the selected provider"""
        if self.provider == "openstreetmap":
            return self.get_osm_route(start_lng, start_lat, end_lng, end_lat)
        elif self.provider == "google":
            return self.get_google_route(start_lng, start_lat, end_lng, end_lat)
        elif self.provider == "here":
            return self.get_here_route(start_lng, start_lat, end_lng, end_lat)
        else:
            return self.get_dummy_route(start_lng, start_lat, end_lng, end_lat)
    
    def get_osm_route(self, start_lng, start_lat, end_lng, end_lat):
        """Use OpenStreetMap's OSRM API (free, no API key required)"""
        try:
            url = f"http://router.project-osrm.org/route/v1/bicycle/{start_lng},{start_lat};{end_lng},{end_lat}"
            params = {
                'overview': 'full',
                'steps': 'true',
                'geometries': 'geojson'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self.parse_osrm_response(data)
        except Exception as e:
            st.warning(f"OSRM routing failed: {e}")
        
        return self.get_dummy_route(start_lng, start_lat, end_lng, end_lat)
    
    def parse_osrm_response(self, data):
        """Parse OSRM response into our standard format"""
        if data.get('code') != 'Ok' or not data.get('routes'):
            return self.get_dummy_route(-0.1278, 51.5074, -0.1220, 51.5120)
        
        route = data['routes'][0]
        legs = data['waypoints']
        
        # Extract turn-by-turn instructions
        steps = []
        for leg in data.get('routes', [])[0].get('legs', []):
            for step in leg.get('steps', []):
                steps.append({
                    'distance': step['distance'],
                    'instruction': step.get('maneuver', {}).get('instruction', 'Continue'),
                    'type': step.get('maneuver', {}).get('type', 'continue')
                })
        
        return {
            'routes': [{
                'distance': route['distance'],
                'duration': route['duration'],
                'geometry': route['geometry'],
                'steps': steps
            }],
            'waypoints': legs
        }
    
    def get_google_route(self, start_lng, start_lat, end_lng, end_lat):
        """Google Maps Directions API"""
        if not self.api_key:
            return self.get_dummy_route(start_lng, start_lat, end_lng, end_lat)
        
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                'origin': f"{start_lat},{start_lng}",
                'destination': f"{end_lat},{end_lng}",
                'mode': 'bicycling',
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self.parse_google_response(data)
        except Exception as e:
            st.error(f"Google Directions API error: {e}")
        
        return self.get_dummy_route(start_lng, start_lat, end_lng, end_lat)
    
    def parse_google_response(self, data):
        """Parse Google Directions API response"""
        if data.get('status') != 'OK' or not data.get('routes'):
            return self.get_dummy_route(-0.1278, 51.5074, -0.1220, 51.5120)
        
        route = data['routes'][0]['legs'][0]
        steps = []
        
        for step in route.get('steps', []):
            steps.append({
                'distance': step['distance']['value'],
                'instruction': step['html_instructions'].replace('<b>', '').replace('</b>', ''),
                'type': self.classify_google_maneuver(step.get('maneuver', ''))
            })
        
        return {
            'routes': [{
                'distance': route['distance']['value'],
                'duration': route['duration']['value'],
                'steps': steps
            }]
        }
    
    def classify_google_maneuver(self, maneuver):
        """Classify Google Maps maneuver types"""
        turn_maneuvers = ['turn-left', 'turn-right', 'turn-slight-left', 'turn-slight-right']
        if maneuver in turn_maneuvers:
            return 'turn'
        elif 'merge' in maneuver or 'fork' in maneuver:
            return 'continue'
        elif 'depart' in maneuver:
            return 'depart'
        elif 'arrive' in maneuver:
            return 'arrive'
        return 'continue'
    
    def get_here_route(self, start_lng, start_lat, end_lng, end_lat):
        """HERE Maps API"""
        if not self.api_key:
            return self.get_dummy_route(start_lng, start_lat, end_lng, end_lat)
        
        try:
            url = "https://router.hereapi.com/v8/routes"
            params = {
                'transportMode': 'bicycle',
                'origin': f"{start_lat},{start_lng}",
                'destination': f"{end_lat},{end_lng}",
                'return': 'polyline,actions,instructions',
                'apiKey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return self.parse_here_response(response.json())
        except Exception as e:
            st.error(f"HERE API error: {e}")
        
        return self.get_dummy_route(start_lng, start_lat, end_lng, end_lat)
    
    def get_dummy_route(self, start_lng, start_lat, end_lng, end_lat):
        """Fallback route with realistic data"""
        # Generate intermediate points for a realistic route
        num_points = 20
        lng_points = np.linspace(start_lng, end_lng, num_points)
        lat_points = np.linspace(start_lat, end_lat, num_points)
        
        # Add some curvature to make it look realistic
        for i in range(1, num_points-1):
            lat_points[i] += np.sin(i * 0.5) * 0.001
        
        coordinates = list(zip(lng_points, lat_points))
        
        instructions = [
            {"distance": 200, "instruction": "Head north on Main Street", "type": "depart"},
            {"distance": 1500, "instruction": "Turn right onto Oak Avenue", "type": "turn"},
            {"distance": 800, "instruction": "Continue straight through the roundabout", "type": "continue"},
            {"distance": 1200, "instruction": "Turn left onto Park Road", "type": "turn"},
            {"distance": 500, "instruction": "Destination on your left", "type": "arrive"}
        ]
        
        return {
            'routes': [{
                'distance': 4200,  # meters
                'duration': 900,   # seconds
                'geometry': {'coordinates': coordinates},
                'steps': instructions
            }],
            'waypoints': [
                {'location': [start_lng, start_lat]},
                {'location': [end_lng, end_lat]}
            ]
        }

class EBikeDashboard:
    def __init__(self):
        self.spotify = SpotifyAPI()
        self.navigation = NavigationAPI()
        self.initialize_session_state()
    
    def initialize_session_state(self):
        default_state = {
            'battery_level': 100,
            'speed': 0,
            'distance': 0,
            'assist_level': 1,
            'is_riding': False,
            'current_song': "Not Playing",
            'destination': "",
            'eta': "00:00",
            'route': None,
            'current_step': 0,
            'spotify_connected': False,
            'auth_code': None,
            'current_location': {"lat": 51.5074, "lng": -0.1278},  # Default: London
            'navigation_provider': 'openstreetmap'
        }
        
        for key, value in default_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

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
    
    def display_spotify_auth(self):
        if not st.session_state.spotify_connected:
            st.markdown("### 🔐 Connect Spotify")
            auth_url = self.spotify.get_auth_url()
            st.markdown(f"[Connect Spotify Account]({auth_url})")
            
            auth_code = st.text_input("Enter authorization code from Spotify:")
            if auth_code and st.button("Connect"):
                if self.spotify.get_tokens(auth_code):
                    st.session_state.spotify_connected = True
                    st.session_state.auth_code = auth_code
                    st.rerun()
    
    def display_spotify_player(self):
        if not st.session_state.spotify_connected:
            self.display_spotify_auth()
            return
            
        st.markdown("""
        <div class="spotify-player">
            <h2>🎵 Spotify Player</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Current playback info
        playback = self.spotify.get_current_playback()
        if playback and playback.get('is_playing'):
            track = playback['item']
            st.session_state.current_song = f"{track['name']} - {track['artists'][0]['name']}"
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(track['album']['images'][0]['url'], width=100)
            with col2:
                st.write(f"**{track['name']}** by {track['artists'][0]['name']}")
                st.write(f"Album: {track['album']['name']}")
        else:
            st.session_state.current_song = "Not Playing"
            st.write("No music currently playing")
        
        # Player controls
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("⏮️ Previous"):
                self.spotify.previous_track()
                st.rerun()
        
        with col2:
            if st.button("⏯️ Play/Pause"):
                if playback and playback.get('is_playing'):
                    self.spotify.pause_playback()
                else:
                    self.spotify.play_track()
                st.rerun()
        
        with col3:
            if st.button("⏭️ Next"):
                self.spotify.next_track()
                st.rerun()
        
        # Search and play
        st.subheader("Search Music")
        search_query = st.text_input("Search for songs, artists, or albums:")
        if search_query:
            results = self.spotify.search_tracks(search_query)
            if results and 'tracks' in results:
                for track in results['tracks']['items'][:5]:
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.image(track['album']['images'][0]['url'] if track['album']['images'] else None, width=50)
                    with col2:
                        if st.button(f"Play {track['name']}", key=track['id']):
                            self.spotify.play_track(track['uri'])
                            st.rerun()
    
    def display_navigation(self):
        st.markdown("""
        <div class="navigation-panel">
            <h2>🧭 Navigation</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation provider selection
        col1, col2 = st.columns(2)
        with col1:
            provider = st.selectbox(
                "Navigation Provider",
                ["openstreetmap", "google", "here"],
                format_func=lambda x: {
                    "openstreetmap": "OpenStreetMap (Free)",
                    "google": "Google Maps",
                    "here": "HERE Maps"
                }[x]
            )
            if provider != st.session_state.navigation_provider:
                st.session_state.navigation_provider = provider
                self.navigation.provider = provider
        
        with col2:
            if provider != "openstreetmap":
                api_key = st.text_input(f"{provider.capitalize()} API Key", type="password")
                if api_key:
                    self.navigation.api_key = api_key
        
        # Destination input
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            destination = st.text_input("Enter Destination Address:", value=st.session_state.destination)
        
        with col2:
            if st.button("📍 Use Current Location"):
                # Simulate getting current location
                st.session_state.current_location = {"lat": 51.5074, "lng": -0.1278}
                st.success("Location set to London")
        
        with col3:
            if st.button("🚴 Start Navigation") and destination:
                self.calculate_route(destination)
        
        if st.session_state.route:
            self.display_route_map()
            self.display_turn_by_turn()
        else:
            st.info("Enter a destination to start navigation")
    
    def calculate_route(self, destination):
        start_lng = st.session_state.current_location["lng"]
        start_lat = st.session_state.current_location["lat"]
        
        # Simulate geocoding - in real app, you'd use a geocoding service
        end_lng, end_lat = start_lng + 0.01, start_lat + 0.01  # Nearby point
        
        route_data = self.navigation.get_route(start_lng, start_lat, end_lng, end_lat)
        st.session_state.route = route_data
        st.session_state.current_step = 0
        st.session_state.destination = destination
        
        # Calculate ETA
        if route_data['routes']:
            duration_min = route_data['routes'][0]['duration'] // 60
            st.session_state.eta = f"{duration_min} min"
    
    def display_route_map(self):
        if not st.session_state.route:
            return
            
        route = st.session_state.route['routes'][0]
        coordinates = route['geometry']['coordinates']
        
        # Create map data
        map_data = pd.DataFrame(coordinates, columns=['lon', 'lat'])
        
        st.subheader("Route Map")
        st.map(map_data, zoom=13)
        
        # Route info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Distance", f"{route['distance']/1000:.1f} km")
        with col2:
            st.metric("Estimated Time", st.session_state.eta)
        with col3:
            st.metric("Calories Burned", f"{(route['distance']/1000 * 30):.0f}")
    
    def display_turn_by_turn(self):
        st.subheader("Turn-by-Turn Directions")
        
        if not st.session_state.route or not st.session_state.route['routes'][0].get('steps'):
            st.info("No turn-by-turn directions available for this route")
            return
        
        instructions = st.session_state.route['routes'][0]['steps']
        current_step = st.session_state.current_step
        
        for i, instruction in enumerate(instructions):
            distance = instruction['distance']
            instruction_text = instruction['instruction']
            step_type = instruction['type']
            
            icon = self.get_direction_icon(step_type)
            distance_text = f"{distance}m" if distance < 1000 else f"{distance/1000:.1f}km"
            
            # Create a unique class for current step
            step_class = "turn-instruction current-step" if i == current_step else "turn-instruction"
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"<h3>{icon}</h3>", unsafe_allow_html=True)
                if i == current_step:
                    st.markdown("**🟢 CURRENT**")
            with col2:
                st.markdown(f"<div class='{step_class}'>"
                           f"<b>{instruction_text}</b><br>"
                           f"<i>{distance_text} ahead</i></div>", unsafe_allow_html=True)
        
        # Navigation controls
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("⬅️ Previous Step") and current_step > 0:
                st.session_state.current_step -= 1
                st.rerun()
        with col2:
            st.write(f"Step {current_step + 1} of {len(instructions)}")
        with col3:
            if st.button("➡️ Next Step") and current_step < len(instructions) - 1:
                st.session_state.current_step += 1
                st.rerun()
    
    def get_direction_icon(self, instruction_type):
        icons = {
            "depart": "🚦 Depart",
            "turn": "↪️ Turn",
            "continue": "⬆️ Continue",
            "arrive": "🏁 Arrive",
            "left": "↩️ Left",
            "right": "↪️ Right"
        }
        return icons.get(instruction_type, "📍")
    
    def display_controls(self):
        st.sidebar.header("eBike Controls")
        
        # Power control
        ride_status = "Stop Ride" if st.session_state.is_riding else "Start Ride"
        if st.sidebar.button(f"🚦 {ride_status}"):
            st.session_state.is_riding = not st.session_state.is_riding
            if st.session_state.is_riding:
                self.start_ride()
            else:
                self.stop_ride()
        
        # Assist level control
        st.sidebar.subheader("Pedal Assist Level")
        new_level = st.sidebar.slider("", 1, 5, st.session_state.assist_level, key="assist_slider")
        if new_level != st.session_state.assist_level:
            st.session_state.assist_level = new_level
        
        # Battery management
        st.sidebar.subheader("Battery Management")
        st.sidebar.progress(st.session_state.battery_level / 100)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🔋 Drain"):
                self.simulate_battery_drain()
        with col2:
            if st.button("🔌 Charge"):
                self.simulate_charge()
        
        # Ride statistics
        st.sidebar.subheader("Ride Statistics")
        st.sidebar.metric("Total Distance", f"{st.session_state.distance:.1f} km")
        st.sidebar.metric("Average Speed", f"{st.session_state.speed:.1f} km/h")
        st.sidebar.metric("CO2 Saved", f"{(st.session_state.distance * 0.2):.1f} kg")
    
    def simulate_battery_drain(self):
        if st.session_state.battery_level > 0:
            st.session_state.battery_level = max(0, st.session_state.battery_level - 10)
    
    def simulate_charge(self):
        if st.session_state.battery_level < 100:
            st.session_state.battery_level = min(100, st.session_state.battery_level + 30)
    
    def start_ride(self):
        st.session_state.is_riding = True
        st.session_state.speed = 15
    
    def stop_ride(self):
        st.session_state.is_riding = False
        st.session_state.speed = 0
    
    def update_ride_data(self):
        if st.session_state.is_riding:
            # Simulate riding data changes
            st.session_state.speed = max(0, min(30, st.session_state.speed + np.random.uniform(-1, 1)))
            st.session_state.distance += st.session_state.speed / 3600
            
            # Battery drains based on speed and assist level
            battery_drain = (st.session_state.speed * st.session_state.assist_level) / 5000
            st.session_state.battery_level = max(0, st.session_state.battery_level - battery_drain)
    
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
        
        # Auto-update ride data
        self.update_ride_data()

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
