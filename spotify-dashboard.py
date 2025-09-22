import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from streamlit_folium import st_folium
import folium

# --- Spotify Setup ---
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

SCOPE = "user-read-playback-state user-modify-playback-state"

# Auth manager
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".cache-spotify"
)

# Probeer cached token te laden
token_info = sp_oauth.get_cached_token()
if not token_info:
    # Nog niet ingelogd → geef loginlink
    auth_url = sp_oauth.get_authorize_url()
    st.write("🔑 [Login met Spotify](" + auth_url + ")")
    redirect_url = st.text_input("Plak hier de volledige URL waar je na login heen werd gestuurd:")

    if redirect_url:
        code = sp_oauth.parse_response_code(redirect_url)
        token_info = sp_oauth.get_access_token(code, as_dict=True)
else:
    st.success("✅ Ingelogd met Spotify!")

sp = None
if token_info:
    sp = spotipy.Spotify(auth=token_info["access_token"])

# --- Tabs ---
tabs = st.tabs(["🎵 Spotify", "🗺️ Navigatie"])

# --- Spotify Controls ---
with tabs[0]:
    st.subheader("Spotify Controls")
    if sp:
        try:
            current = sp.current_playback()
        except Exception:
            current = None

        if current and current.get("item"):
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
            st.info("Geen muziek aan het spelen of geen device actief.")
    else:
        st.warning("⚠️ Eerst inloggen met Spotify.")

# --- Navigatie Tab ---
with tabs[1]:
    st.subheader("Navigatie")

    def geocode_location(place):
        url = f"https://nominatim.openstreetmap.org/search?q={place}&format=json&limit=1"
        r = requests.get(url, headers={"User-Agent": "streamlit-spotify-dashboard"})
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])

    def get_route(start_coords, end_coords):
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
                folium.PolyLine(
                    locations=[(lat, lon) for lon, lat in route],
                    color="lime",
                    weight=5
                ).add_to(m)
                st_folium(m, width=700, height=400)

                st.subheader("🚦 Instructies")
                for i, step in enumerate(steps, 1):
                    st.write(f"**{i}.** {step}")
            else:
                st.error("Geen route gevonden.")
        else:
            st.error("Kon locaties niet vinden.")

