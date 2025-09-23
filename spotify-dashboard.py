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
# Custom CSS voor CarPlay look
# --------------------------
st.markdown("""
<style>
/* Hele achtergrond */
body, .main {
    background-color: #000000;
    color: white;
}

/* CarPlay Tile */
.carplay-tile {
    background: linear-gradient(145deg, #111111, #1c1c1c);
    border-radius: 25px;
    padding: 20px;
    margin: 15px auto;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.7);
    color: white;
}

/* Spotify Tile */
.spotify-tile {
    background: linear-gradient(180deg, #000000, #121212);
    text-align: center;
}

/* Navigatie Tile */
.nav-tile {
    background: linear-gradient(180deg, #1c1c1c, #2b2b2b);
    text-align: center;
}

/* Spotify Logo */
.spotify-header img {
    width: 140px;
    margin-bottom: 15px;
}

/* Track Info */
.track-info {
    font-size: 18px;
    margin: 8px 0;
}

/* Album cover */
.cover img {
    width: 150px;
    border-radius: 15px;
    box-shadow: 0px 0px 25px #1DB954;
    margin: 10px 0;
}

/* Controls Spotify */
.controls {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 40px;
    margin-top: 20px;
}
button[title="Play/Pause"], button[title="Previous"], button[title="Next"] {
    border: none;
    border-radius: 50%;
    padding: 15px;
    font-size: 24px;
    background: #1DB954;
    color: white;
}
button:hover {
    background: #1ed760 !important;
}
</style>
""", unsafe_allow_html=True)

# --------------------------
# TILE 1 - Spotify
# --------------------------
st.markdown('<div class="carplay-tile spotify-tile">', unsafe_allow_html=True)
st.markdown(
    '<div class="spotify-header"><img src="https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_Green.png"></div>',
    unsafe_allow_html=True
)

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
            if st.button("⏮️", key="prev", help="Previous"):
                sp.previous_track()
        with col2:
            if st.button("⏯️", key="playpause", help="Play/Pause"):
                if track["is_playing"]:
                    sp.pause_playback()
                else:
                    sp.start_playback()
        with col3:
            if st.button("⏭️", key="next", help="Next"):
                sp.next_track()
    else:
        st.write("🎶 Niks speelt momenteel...")
except Exception as e:
    st.error(f"Spotify error: {e}")

st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# TILE 2 - Navigatie
# --------------------------
st.markdown('<div class="carplay-tile nav-tile">', unsafe_allow_html=True)
st.subheader("🗺️ Navigatie")

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

        st_folium(m, width=700, height=400)
    except:
        st.error("❌ Ongeldige coördinaten. Gebruik format: lat, lon (bijv. 52.37, 4.89).")

st.markdown('</div>', unsafe_allow_html=True)

