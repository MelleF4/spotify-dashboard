import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import polyline
import folium
from streamlit_folium import st_folium

# ========================
# Spotify instellingen
# ========================
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

SCOPE = "user-read-playback-state,user-modify-playback-state"

# Spotify authenticatie
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
)

if "token_info" not in st.session_state:
    auth_url = sp_oauth.get_authorize_url()
    st.write("### Stap 1: Log in bij Spotify")
    st.markdown(f"[Klik hier om in te loggen bij Spotify]({auth_url})")

    code = st.text_input("### Stap 2: Plak hier de code uit de URL na inloggen")

    if code:
        token_info = sp_oauth.get_access_token(code)
        st.session_state["token_info"] = token_info
        st.experimental_rerun()

# ========================
# Spotify dashboard
# ========================
if "token_info" in st.session_state:
    token_info = st.session_state["token_info"]
    sp = spotipy.Spotify(auth=token_info["access_token"])

    st.markdown(
        """
        <style>
        body { background-color: black; }
        .carplay-card {
            background-color: #121212;
            border-radius: 20px;
            padding: 20px;
            color: white;
            text-align: center;
            margin-bottom: 20px;
        }
        .spotify-logo {
            width: 60px;
            margin-bottom: 15px;
        }
        .song-title {
            font-size: 22px;
            font-weight: bold;
        }
        .song-artist {
            font-size: 18px;
            color: #b3b3b3;
        }
        .controls button {
            margin: 0 15px;
            background: none;
            border: none;
            color: white;
            font-size: 28px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Huidig nummer ophalen
    current = sp.current_playback()

    st.markdown('<div class="carplay-card">', unsafe_allow_html=True)
    st.image("https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg", width=80)

    if current and current.get("item"):
        song = current["item"]["name"]
        artists = ", ".join([a["name"] for a in current["item"]["artists"]])
        album_cover = current["item"]["album"]["images"][0]["url"]

        st.image(album_cover, width=250)
        st.markdown(f'<div class="song-title">{song}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="song-artist">{artists}</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⏮️"):
                sp.previous_track()
        with col2:
            if st.button("⏯️"):
                if current["is_playing"]:
                    sp.pause_playback()
                else:
                    sp.start_playback()
        with col3:
            if st.button("⏭️"):
                sp.next_track()

    else:
        st.write("Geen muziek speelt momenteel.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ========================
    # Navigatie
    # ========================
    st.markdown('<div class="carplay-card">', unsafe_allow_html=True)
    st.write("### Navigatie")

    start = st.text_input("Startlocatie (lat,lon)", "52.3676,4.9041")  # Amsterdam
    end = st.text_input("Eindlocatie (lat,lon)", "52.0907,5.1214")    # Utrecht

    if st.button("📍 Route tonen"):
        try:
            start_coords = tuple(map(float, start.split(",")))
            end_coords = tuple(map(float, end.split(",")))

            url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=polyline"
            r = requests.get(url)
            data = r.json()

            if "routes" in data and len(data["routes"]) > 0:
                route = data["routes"][0]["geometry"]
                points = polyline.decode(route)

                m = folium.Map(location=start_coords, zoom_start=8)
                folium.Marker(start_coords, tooltip="Start").add_to(m)
                folium.Marker(end_coords, tooltip="Eind").add_to(m)
                folium.PolyLine(points, color="blue", weight=5).add_to(m)

                st_folium(m, width=700, height=500)
            else:
                st.error("Geen route gevonden.")
        except Exception as e:
            st.error(f"Fout bij routeberekening: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

