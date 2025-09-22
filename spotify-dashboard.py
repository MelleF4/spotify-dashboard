import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import requests
from streamlit_folium import st_folium
import folium

# --- Spotify API Setup ---
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
SCOPE = "user-read-playback-state user-modify-playback-state"

auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
)
sp = spotipy.Spotify(auth_manager=auth_manager)

# --- Geocoding + Routing (met caching) ---
@st.cache_data(ttl=3600)
def geocode_location(place):
    """Geef coördinaten terug voor een adres via Nominatim (OSM)."""
    url = f"https://nominatim.openstreetmap.org/search?q={place}&format=json&limit=1"
    r = requests.get(url, headers={"User-Agent": "streamlit-spotify-dashboard"})
    data = r.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])

@st.cache_data(ttl=1800)
def get_route(start_coords, end_coords):
    """Haal route op van OSRM tussen twee coördinaten."""
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
        f"?overview=full&geometries=geojson&steps=true"
    )
    r = requests.get(url)
    data = r.json()
    if data.get("code") != "Ok":
        return None, []
    route = data["routes"][0]["geometry"]["coordinates"]
    steps = []
    for leg in data["routes"][0]["legs"]:
        for step in leg["steps"]:
            steps.append(step["maneuver"]["instruction"])
    return route, steps

# --- UI Tabs ---
tabs = st.tabs(["🎵 Spotify", "📊 Ritdata", "⚙️ Instellingen", "📈 Grafieken", "🗺️ Navigatie"])

# --- Spotify Tab ---
with tabs[0]:
    st.subheader("Spotify Controls")

    try:
        current = sp.current_playback()
    except Exception:
        current = None

    if current and current.get("is_playing"):
        track = current["item"]["name"]
        artist = current["item"]["artists"][0]["name"]
        cover = current["item"]["album"]["images"][1]["url"]

        st.image(cover, width=120)
        st.markdown(f"**{track}** – {artist}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⏮️ Vorige"):
                sp.previous_track()
        with col2:
            if st.button("⏯️ Play/Pause"):
                if current["is_playing"]:
                    sp.pause_playback()
                else:
                    sp.start_playback()
        with col3:
            if st.button("⏭️ Volgende"):
                sp.next_track()
    else:
        st.info("Geen muziek aan het spelen.")

# --- Ritdata Tab ---
with tabs[1]:
    st.subheader("Ritten loggen")
    if "ritten" not in st.session_state:
        st.session_state["ritten"] = []

    afstand = st.number_input("Afstand (km)", min_value=0.0, step=0.1)
    tijd = st.text_input("Tijd (bijv. 45m of 1h15m)")

    if st.button("➕ Rit toevoegen"):
        st.session_state["ritten"].append({"Afstand (km)": afstand, "Tijd": tijd})
        st.success("Rit toegevoegd!")

    if st.session_state["ritten"]:
        df = pd.DataFrame(st.session_state["ritten"])
        st.table(df)

# --- Instellingen Tab ---
with tabs[2]:
    st.subheader("Instellingen")
    st.write("Hier kun je toekomstige instellingen plaatsen (bijv. thema, refresh-tijd).")

# --- Grafieken Tab ---
with tabs[3]:
    st.subheader("Rit Grafieken (basis)")
    if "ritten" in st.session_state and st.session_state["ritten"]:
        df = pd.DataFrame(st.session_state["ritten"])
        st.bar_chart(df["Afstand (km)"])
    else:
        st.info("Nog geen ritten om weer te geven.")

# --- Navigatie Tab ---
with tabs[4]:
    st.subheader("Navigatie")

    col1, col2 = st.columns(2)
    with col1:
        start = st.text_input("Startlocatie", "Amsterdam Centraal")
    with col2:
        end = st.text_input("Bestemming", "Rotterdam Centraal")

    if st.button("📍 Bereken route"):
        start_coords = geocode_location(start)
        end_coords = geocode_location(end)

        if start_coords and end_coords:
            route, steps = get_route(start_coords, end_coords)

            if route:
                m = folium.Map(location=start_coords, zoom_start=7, tiles="cartodb dark_matter")
                folium.Marker(start_coords, tooltip="Start").add_to(m)
                folium.Marker(end_coords, tooltip="Bestemming").add_to(m)
                folium.PolyLine(locations=[(lat, lon) for lon, lat in route],
                                color="lime", weight=5).add_to(m)
                st_folium(m, width=700, height=400)

                st.subheader("🚦 Instructies")
                for i, step in enumerate(steps, 1):
                    st.write(f"**{i}.** {step}")
            else:
                st.error("Geen route gevonden.")
        else:
            st.error("Kon locaties niet vinden.")
