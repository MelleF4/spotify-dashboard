import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import folium
from streamlit_folium import st_folium

# --------------------------
# Config
# --------------------------
st.set_page_config(page_title="CarPlay Dashboard", layout="wide")

CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope,
    cache_path=".cache"
)

sp = spotipy.Spotify(auth_manager=sp_oauth)

# --------------------------
# Tabs (CarPlay feeling)
# --------------------------
tab1, tab2 = st.tabs(["🎵 Spotify", "🗺️ Navigatie"])

# --------------------------
# TAB 1 - Spotify
# --------------------------
with tab1:
    st.markdown(
        """
        <style>
        .spotify-header {
            text-align: center;
            margin-bottom: 20px;
        }
        .spotify-header img {
            width: 120px;
        }
        .track-info {
            text-align: center;
            font-size: 18px;
            margin: 10px 0;
        }
        .cover {
            display: flex;
            justify-content: center;
            margin: 15px 0;
        }
        .cover img {
            width: 180px;
            border-radius: 20px;
            box-shadow: 0px 0px 20px #1DB954;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="spotify-header"><img src="https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_Green.png"></div>', unsafe_allow_html=True)

    try:
        track = sp.current_playback()
        if track and track["is_playing"]:
            item = track["item"]
            name = item["name"]
            artist = ", ".join([a["name"] for a in item["artists"]])
            album_cover = item["album"]["images"][1]["url"]

            st.markdown(f'<div class="track-info"><b>{name}</b><br>{artist}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cover"><img src="{album_cover}"></div>', unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⏮️ Vorige"):
                    sp.previous_track()
            with col2:
                if st.button("⏯️ Play/Pauze"):
                    if track["is_playing"]:
                        sp.pause_playback()
                    else:
                        sp.start_playback()
            with col3:
                if st.button("⏭️ Volgende"):
                    sp.next_track()
        else:
            st.write("Niks speelt momenteel...")
    except Exception as e:
        st.error(f"Spotify error: {e}")

# --------------------------
# TAB 2 - Navigatie
# --------------------------
with tab2:
    st.subheader("🗺️ Kaart")

    start = st.text_input("Startpunt (lat, lon)", "52.3702, 4.8952")  # Amsterdam
    end = st.text_input("Bestemming (lat, lon)", "52.0907, 5.1214")   # Utrecht

    if st.button("Toon route"):
        try:
            start_coords = [float(x) for x in start.split(",")]
            end_coords = [float(x) for x in end.split(",")]

            m = folium.Map(location=start_coords, zoom_start=10)
            folium.Marker(start_coords, tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(end_coords, tooltip="Bestemming", icon=folium.Icon(color="red")).add_to(m)
            folium.PolyLine([start_coords, end_coords], color="blue", weight=5).add_to(m)

            st_folium(m, width=700, height=500)
        except:
            st.error("Ongeldige coördinaten. Gebruik format: lat, lon (bijv. 52.37, 4.89).")


