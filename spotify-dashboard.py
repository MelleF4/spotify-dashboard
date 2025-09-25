import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import requests
import json
import os
from typing import Dict, List, Optional
import spotipy
from spotipy.oauth2 import SpotifyOAuth
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
    .spotify-button {
        background-color: #1DB954;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 20px;
        cursor: pointer;
        font-weight: bold;
    }
    .graphhopper-attribution {
        font-size: 0.8rem;
        color: #666;
        text-align: center;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

class SpotifyManager:
    def __init__(self):
        self.client_id = st.secrets.get("SPOTIFY_CLIENT_ID", "")
        self.client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET", "")
        self.redirect_uri = "http://localhost:8501"
        self.scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing streaming user-read-email user-read-private"
        self.sp = None
        self.initialize_spotify()
    
    def initialize_spotify(self):
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=".spotify_cache",
                show_dialog=True
            ))
            if self.sp.current_user():
                st.session_state.spotify_connected = True
                return True
        except Exception as e:
            st.session_state.spotify_connected = False
        return False
    
    def get_auth_url(self):
        try:
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=".spotify_cache",
                show_dialog=True
            )
            return auth_manager.get_authorize_url()
        except Exception as e:
            st.error(f"Error getting auth URL: {e}")
            return None
    
    def get_current_playback(self):
        try:
            return self.sp.current_playback()
        except Exception as e:
            st.error(f"Error getting playback: {e}")
            return None
    
    def play_track(self, track_uri=None, context_uri=None):
        try:
            if track_uri:
                self.sp.start_playback(uris=[track_uri])
            elif context_uri:
                self.sp.start_playback(context_uri=context_uri)
            else:
                self.sp.start_playback()
            return True
        except Exception as e:
            st.error(f"Error playing track: {e}")
            return False
    
    def pause_playback(self):
        try:
            self.sp.pause_playback()
            return True
        except Exception as e:
            st.error(f"Error pausing playback: {e}")
            return False
    
    def next_track(self):
        try:
            self.sp.next_track()
            return True
        except Exception as e:
            st.error(f"Error skipping track: {e}")
            return False
    
    def previous_track(self):
        try:
            self.sp.previous_track()
            return True
        except Exception as e:
            st.error(f"Error going to previous track: {e}")
            return False
    
    def search_tracks(self, query, limit=10):
        try:
            results = self.sp.search(q=query, limit=limit, type='track')
            return results
        except Exception as e:
            st.error(f"Error searching tracks: {e}")
            return None
    
    def set_volume(self, volume):
        try:
            self.sp.volume(volume)
            return True
        except Exception as e:
            st.error(f"Error setting volume: {e}")
            return False

class GraphHopperNavigation:
    def __init__(self):
        self.api_key = st.secrets.get("GRAPHHOPPER_API_KEY", "")
        # You can use the public instance or your own hosted instance
        self.base_url = "https://graphhopper.com/api/1/route"
        
    def geocode_address(self, address):
        """Geocode an address using GraphHopper Geocoding"""
        if not self.api_key:
            return None
            
        geocode_url = "https://graphhopper.com/api/1/geocode"
        params = {
            'q': address,
            'limit': 1,
            'key': self.api_key
        }
        
        try:
            response = requests.get(geocode_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['hits']:
                    location = data['hits'][0]['point']
                    return {'lat': location['lat'], 'lng': location['lng']}
        except Exception as e:
            st.error(f"Geocoding error: {e}")
        
        return None
    
    def get_route(self, start_address, end_address, vehicle="bike"):
        """Get route with turn-by-turn directions using GraphHopper"""
        if not self.api_key:
            st.warning("Using demo data - add GraphHopper API key for real routing")
            return self.get_dummy_route()
        
        # Geocode addresses
        start_coords = self.geocode_address(start_address)
        end_coords = self.geocode_address(end_address)
        
        if not start_coords or not end_coords:
            st.error("Kon adressen niet vinden. Controleer de spelling.")
            return self.get_dummy_route()
        
        params = {
            'key': self.api_key,
            'vehicle': vehicle,
            'locale': 'nl',
            'instructions': True,
            'calc_points': True,
            'points_encoded': False,  # Get full coordinates
            'elevation': True,
            'optimize': 'true'
        }
        
        # GraphHopper expects points as "lat,lng"
        points = [
            f"{start_coords['lat']},{start_coords['lng']}",
            f"{end_coords['lat']},{end_coords['lng']}"
        ]
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'paths' in data and data['paths']:
                    return self.parse_graphhopper_response(data)
                else:
                    st.error("Geen route gevonden. Probeer andere adressen.")
            else:
                st.error(f"GraphHopper API error: {response.status_code}")
                
        except Exception as e:
            st.error(f"GraphHopper API error: {e}")
        
        return self.get_dummy_route()
    
    def parse_graphhopper_response(self, data):
        """Parse GraphHopper response into our standard format"""
        path = data['paths'][0]
        
        # Extract turn-by-turn instructions
        steps = []
        for instruction in path.get('instructions', []):
            steps.append({
                'distance': instruction.get('distance', 0),
                'instruction': instruction.get('text', ''),
                'type': self.classify_instruction(instruction),
                'direction': instruction.get('sign', 0),
                'time': instruction.get('time', 0) // 1000  # Convert to seconds
            })
        
        # Extract route geometry
        coordinates = path.get('points', {}).get('coordinates', [])
        
        return {
            'routes': [{
                'distance': path.get('distance', 0),
                'duration': path.get('time', 0) // 1000,  # Convert to seconds
                'geometry': {'coordinates': coordinates},
                'steps': steps,
                'elevation': path.get('ascend', 0),
                'descent': path.get('descend', 0)
            }],
            'info': {
                'copyright': 'GraphHopper',
                'took': data.get('info', {}).get('took', 0)
            }
        }
    
    def classify_instruction(self, instruction):
        """Classify instruction type for icons based on GraphHopper sign codes"""
        sign = instruction.get('sign', 0)
        
        # GraphHopper sign codes:
        # -3 = sharp left, -2 = left, -1 = slight left
        # 0 = continue/straight
        # 1 = slight right, 2 = right, 3 = sharp right
        # 4 = finish, 5 = via, 6 = roundabout
        
        if sign == 4:  # Finish
            return 'arrive'
        elif sign == 6:  # Roundabout
            return 'roundabout'
        elif sign in [-3, -2, -1]:  # Left turns
            return 'turn-left'
        elif sign in [1, 2, 3]:  # Right turns
            return 'turn-right'
        elif sign == 0:  # Continue
            return 'continue'
        else:
            return 'continue'
    
    def get_direction_icon_from_sign(self, sign):
        """Get icon based on GraphHopper sign code"""
        icons = {
            -3: '↰',  # Sharp left
            -2: '↩️',  # Left
            -1: '↖️',  # Slight left
            0: '⬆️',   # Continue
            1: '↗️',   # Slight right
            2: '↪️',   # Right
            3: '↱',    # Sharp right
            4: '🏁',   # Arrive
            6: '🔄'    # Roundabout
        }
        return icons.get(sign, '📍')
    
    def get_dummy_route(self):
        """Fallback route data voor demo"""
        instructions = [
            {"distance": 200, "instruction": "Vertrek vanaf startpunt", "type": "depart", "direction": 0, "time": 30},
            {"distance": 1500, "instruction": "Rechtsaf slaan op Hoofdstraat", "type": "turn-right", "direction": 2, "time": 200},
            {"distance": 800, "instruction": "Rechtdoor op rotonde", "type": "roundabout", "direction": 6, "time": 100},
            {"distance": 1200, "instruction": "Linksaf slaan op Parkweg", "type": "turn-left", "direction": -2, "time": 180},
            {"distance": 500, "instruction": "Bestemming bereikt", "type": "arrive", "direction": 4, "time": 60}
        ]
        
        # Demo coordinates for Amsterdam area
        coordinates = [
            [4.8970, 52.3779], [4.8980, 52.3785], [4.8990, 52.3790],
            [4.9000, 52.3795], [4.9010, 52.3800], [4.9020, 52.3805],
            [4.9030, 52.3810]
        ]
        
        return {
            'routes': [{
                'distance': 4200,
                'duration': 900,
                'geometry': {'coordinates': coordinates},
                'steps': instructions,
                'elevation': 15,
                'descent': 12
            }],
            'info': {
                'copyright': 'GraphHopper Demo',
                'took': 50
            }
        }

class EBikeDashboard:
    def __init__(self):
        self.spotify = SpotifyManager()
        self.navigation = GraphHopperNavigation()
        self.initialize_session_state()
    
    def initialize_session_state(self):
        default_state = {
            'battery_level': 100,
            'speed': 0,
            'distance': 0,
            'assist_level': 1,
            'is_riding': False,
            'current_song': "Niet actief",
            'destination': "",
            'current_address': "Amsterdam, Nederland",
            'eta': "00:00",
            'route': None,
            'current_step': 0,
            'spotify_connected': False,
            'volume': 50,
            'total_calories': 0,
            'vehicle_type': 'bike'
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
                <h3>🔋 Accu</h3>
                <h2>{st.session_state.battery_level}%</h2>
                <progress value="{st.session_state.battery_level}" max="100"></progress>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>⚡ Snelheid</h3>
                <h2>{st.session_state.speed} km/h</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📏 Afstand</h3>
                <h2>{st.session_state.distance:.1f} km</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🔥 Calorieën</h3>
                <h2>{st.session_state.total_calories:.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
    
    def display_spotify_auth(self):
        st.markdown("### 🔐 Verbind met Spotify")
        st.write("Klik op de knop om je Spotify account te verbinden:")
        
        auth_url = self.spotify.get_auth_url()
        if auth_url:
            st.markdown(f'<a href="{auth_url}" target="_blank"><button class="spotify-button">Spotify Verbinden</button></a>', 
                       unsafe_allow_html=True)
        
        st.info("Na het klikken word je doorgestuurd naar Spotify. Autoriseer de app en je komt terug in het dashboard.")
        
        try:
            query_params = st.experimental_get_query_params()
            if 'code' in query_params:
                code = query_params['code'][0]
                st.success("Succesvol verbonden met Spotify!")
                st.session_state.spotify_connected = True
                st.experimental_set_query_params()
        except:
            pass
    
    def display_spotify_player(self):
        if not st.session_state.spotify_connected:
            self.display_spotify_auth()
            return
        
        st.markdown("""
        <div class="spotify-player">
            <h2>🎵 Spotify Speler</h2>
        </div>
        """, unsafe_allow_html=True)
        
        playback = self.spotify.get_current_playback()
        
        if playback and playback.get('is_playing'):
            track = playback['item']
            artists = ", ".join([artist['name'] for artist in track['artists']])
            st.session_state.current_song = f"{track['name']} - {artists}"
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if track['album']['images']:
                    st.image(track['album']['images'][0]['url'], width=150)
            with col2:
                st.write(f"**🎵 Nu aan het spelen**")
                st.write(f"**{track['name']}**")
                st.write(f"**Door:** {artists}")
                st.write(f"**Album:** {track['album']['name']}")
                
                if playback.get('progress_ms') and track['duration_ms']:
                    progress = playback['progress_ms'] / track['duration_ms']
                    st.progress(progress)
                    current_time = str(timedelta(milliseconds=playback['progress_ms']))[2:7]
                    total_time = str(timedelta(milliseconds=track['duration_ms']))[2:7]
                    st.write(f"{current_time} / {total_time}")
        else:
            st.session_state.current_song = "Niet actief"
            st.write("**Er wordt momenteel geen muziek afgespeeld**")
        
        # Bedieningselementen
        st.subheader("Speler Bediening")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("⏮️ Vorige"):
                if self.spotify.previous_track():
                    st.rerun()
        
        with col2:
            if playback and playback.get('is_playing'):
                if st.button("⏸️ Pause"):
                    if self.spotify.pause_playback():
                        st.rerun()
            else:
                if st.button("▶️ Afspelen"):
                    if self.spotify.play_track():
                        st.rerun()
        
        with col3:
            if st.button("⏭️ Volgende"):
                if self.spotify.next_track():
                    st.rerun()
        
        with col4:
            new_volume = st.slider("🔊 Volume", 0, 100, st.session_state.volume)
            if new_volume != st.session_state.volume:
                if self.spotify.set_volume(new_volume):
                    st.session_state.volume = new_volume
        
        with col5:
            if st.button("🔄 Vernieuwen"):
                st.rerun()
        
        # Zoekfunctionaliteit
        st.subheader("🔍 Zoek Muziek")
        search_query = st.text_input("Zoek naar nummers, artiesten of albums:")
        if search_query:
            results = self.spotify.search_tracks(search_query, limit=5)
            if results and 'tracks' in results:
                st.write("### Zoekresultaten")
                for track in results['tracks']['items']:
                    artists = ", ".join([artist['name'] for artist in track['artists']])
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        if track['album']['images']:
                            st.image(track['album']['images'][0]['url'], width=60)
                    with col2:
                        st.write(f"**{track['name']}**")
                        st.write(f"*{artists}*")
                    with col3:
                        if st.button("Afspelen", key=track['id']):
                            if self.spotify.play_track(track['uri']):
                                st.success(f"Speelt af: {track['name']}")
                                st.rerun()

    def display_navigation(self):
        st.markdown("""
        <div class="navigation-panel">
            <h2>🧭 GraphHopper Navigatie</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("🚴 Gebruik GraphHopper voor optimale fietsroutes met turn-by-turn instructies")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📍 Startadres")
            start_address = st.text_input("Huidige locatie", 
                                        value=st.session_state.current_address,
                                        help="Vul je startadres in")
        
        with col2:
            st.subheader("🎯 Bestemming")
            destination = st.text_input("Waar naartoe?", 
                                      value=st.session_state.destination,
                                      placeholder="Vul je bestemming in")
        
        # Voertuigtype selectie
        col1, col2 = st.columns(2)
        with col1:
            vehicle_type = st.selectbox(
                "Voertuigtype",
                ["bike", "racingbike", "mtb", "foot"],
                format_func=lambda x: {
                    "bike": "🚲 Standaard Fiets",
                    "racingbike": "🚴 Racefiets",
                    "mtb": "🚵 Mountainbike",
                    "foot": "🚶‍♂️ Lopen"
                }[x]
            )
        
        if st.button("🚴 Route Berekenen", type="primary"):
            if start_address and destination:
                with st.spinner("Berekenen optimale route..."):
                    route_data = self.navigation.get_route(start_address, destination, vehicle_type)
                    if route_data:
                        st.session_state.route = route_data
                        st.session_state.current_step = 0
                        st.session_state.destination = destination
                        st.session_state.current_address = start_address
                        st.session_state.vehicle_type = vehicle_type
                        
                        if route_data['routes']:
                            duration_min = route_data['routes'][0]['duration'] // 60
                            st.session_state.eta = f"{duration_min} min"
                            st.success(f"Route gevonden! Geschatte tijd: {duration_min} minuten")
                    else:
                        st.error("Kon route niet berekenen. Controleer de adressen.")
            else:
                st.warning("Vul zowel startadres als bestemming in.")
        
        if st.session_state.route:
            self.display_route_map()
            self.display_turn_by_turn()
        else:
            st.info("Vul startadres en bestemming in om je route te berekenen")
    
    def display_route_map(self):
        if not st.session_state.route:
            return
            
        route = st.session_state.route['routes'][0]
        coordinates = route['geometry']['coordinates']
        
        # GraphHopper geeft [lng, lat] terug, Streamlit wil [lat, lng]
        map_data = pd.DataFrame(coordinates, columns=['lon', 'lat'])
        
        st.subheader("🗺️ Route Overzicht")
        st.map(map_data, zoom=12)
        
        # Route samenvatting
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Totale Afstand", f"{route['distance']/1000:.1f} km")
        with col2:
            st.metric("Geschatte Tijd", st.session_state.eta)
        with col3:
            st.metric("Hoogteverschil", f"{route.get('elevation', 0):.0f} m")
        with col4:
            st.metric("CO2 Besparing", f"{(route['distance']/1000 * 0.2):.1f} kg")
        
        st.markdown('<div class="graphhopper-attribution">Route data © GraphHopper</div>', 
                   unsafe_allow_html=True)
    
    def display_turn_by_turn(self):
        st.subheader("🔄 Turn-by-Turn Instructies")
        
        if not st.session_state.route or not st.session_state.route['routes'][0].get('steps'):
            st.info("Geen turn-by-turn instructies beschikbaar")
            return
        
        instructions = st.session_state.route['routes'][0]['steps']
        current_step = st.session_state.current_step
        
        # Huidige stap prominent weergeven
        if current_step < len(instructions):
            current_instruction = instructions[current_step]
            icon = self.navigation.get_direction_icon_from_sign(current_instruction.get('direction', 0))
            st.markdown(f"### 🟢 Huidig: {icon} {current_instruction['instruction']}")
            st.write(f"**Afstand tot volgende actie:** {current_instruction['distance']:.0f}m")
            st.write(f"**Tijd:** {current_instruction['time']} seconden")
        
        st.write("---")
        st.write("### Volledige Route Instructies:")
        
        for i, instruction in enumerate(instructions):
            distance = instruction['distance']
            instruction_text = instruction['instruction']
            direction = instruction.get('direction', 0)
            time_sec = instruction.get('time', 0)
            
            icon = self.navigation.get_direction_icon_from_sign(direction)
            distance_text = f"{distance:.0f}m" if distance < 1000 else f"{distance/1000:.1f}km"
            
            step_class = "turn-instruction current-step" if i == current_step else "turn-instruction"
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"<h3>{icon}</h3>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='{step_class}'>"
                           f"<b>{instruction_text}</b><br>"
                           f"<i>{distance_text} • {time_sec}s</i></div>", 
                           unsafe_allow_html=True)
        
        # Navigatie bediening
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Vorige Stap") and current_step > 0:
                st.session_state.current_step -= 1
                st.rerun()
        with col2:
            st.write(f"**Stap {current_step + 1} van {len(instructions)}**")
            st.progress((current_step + 1) / len(instructions))
        with col3:
            if st.button("➡️ Volgende Stap") and current_step < len(instructions) - 1:
                st.session_state.current_step += 1
                st.rerun()
    
    def display_controls(self):
        st.sidebar.header("eBike Bediening")
        
        ride_status = "Rit Stoppen" if st.session_state.is_riding else "Rit Starten"
        if st.sidebar.button(f"🚦 {ride_status}", use_container_width=True):
            st.session_state.is_riding = not st.session_state.is_riding
            if st.session_state.is_riding:
                self.start_ride()
            else:
                self.stop_ride()
        
        st.sidebar.subheader("Ondersteuningsniveau")
        new_level = st.sidebar.slider("", 1, 5, st.session_state.assist_level, key="assist_slider")
        if new_level != st.session_state.assist_level:
            st.session_state.assist_level = new_level
        
        st.sidebar.subheader("Accu Beheer")
        st.sidebar.progress(st.session_state.battery_level / 100)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🔋 Verbruik", use_container_width=True):
                self.simulate_battery_drain()
        with col2:
            if st.button("🔌 Opladen", use_container_width=True):
                self.simulate_charge()
        
        st.sidebar.subheader("Rit Statistieken")
        st.sidebar.metric("Totale Afstand", f"{st.session_state.distance:.1f} km")
        st.sidebar.metric("Gemiddelde Snelheid", f"{st.session_state.speed:.1f} km/h")
        st.sidebar.metric("Calorieën Verbrand", f"{st.session_state.total_calories:.0f}")
        st.sidebar.metric("CO2 Bespaard", f"{(st.session_state.distance * 0.2):.1f} kg")
    
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
            st.session_state.speed = max(0, min(30, st.session_state.speed + np.random.uniform(-1, 1)))
            st.session_state.distance += st.session_state.speed / 3600
            battery_drain = (st.session_state.speed * st.session_state.assist_level) / 5000
            st.session_state.battery_level = max(0, st.session_state.battery_level - battery_drain)
            st.session_state.total_calories = st.session_state.distance * 40
    
    def run(self):
        self.display_header()
        self.display_metrics()
        
        tab1, tab2, tab3 = st.tabs(["🎵 Muziek", "🧭 Navigatie", "📊 Statistieken"])
        
        with tab1:
            self.display_spotify_player()
        
        with tab2:
            self.display_navigation()
        
        with tab3:
            self.display_statistics()
        
        self.display_controls()
        self.update_ride_data()

    def display_statistics(self):
        st.subheader("📊 Rit Statistieken")
        
        dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
        ride_data = pd.DataFrame({
            'Date': dates,
            'Distance': np.random.uniform(5, 25, len(dates)),
            'Average Speed': np.random.uniform(12, 22, len(dates)),
            'Calories Burned': np.random.uniform(150, 400, len(dates))
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.line_chart(ride_data.set_index('Date')['Distance'])
            st.write("Dagelijkse Afstand (km)")
        
        with col2:
            st.line_chart(ride_data.set_index('Date')['Average Speed'])
            st.write("Gemiddelde Snelheid (km/h)")
        
        st.subheader("Maandoverzicht")
        summary_cols = st.columns(4)
        with summary_cols[0]:
            st.metric("Totale Afstand", f"{ride_data['Distance'].sum():.1f} km")
        with summary_cols[1]:
            st.metric("Totaal Ritten", len(ride_data))
        with summary_cols[2]:
            st.metric("Totaal Calorieën", f"{ride_data['Calories Burned'].sum():.0f}")
        with summary_cols[3]:
            st.metric("CO2 Bespaard", f"{(ride_data['Distance'].sum() * 0.2):.1f} kg")

# Run the dashboard
if __name__ == "__main__":
    dashboard = EBikeDashboard()
    dashboard.run()
