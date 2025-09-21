import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from io import BytesIO
from PIL import Image
from colorthief import ColorThief

# -----------------------------
# Spotify API setup met Streamlit Secrets
# -----------------------------
SPOTIPY_CLIENT_ID = st.secrets["CLIENT_ID"]
SPOTIPY_CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
SPOTIPY_REDIRECT_URI = st.secrets["REDIRECT_URI"]

SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE
))

# -----------------------------
# Helper functies
# -----------------------------
def get_current_track():
    current = sp.current_playback()
    if not current or not current.get("item"):
        return None

    track = current["item"]
    artist = ", ".join([a["name"] for a in track["artists"]])
    album_cover_url = track["album"]["images"][0]["url"]

    try:
        color_thief = ColorThief(BytesIO(requests.get(album_cover_url).content))
        dominant_color = color_thief.get_color(quality=1)
    except:
        dominant_color = (30, 215, 96)  # Spotify green fallback

    return {
        "title": track["name"],
        "artist": artist,
        "cover_url": album_cover_url,
        "dominant_color": dominant_color,
        "is_playing": current["is_playing"]
    }

def media_controls():
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("⏮", use_container_width=True):
            sp.previous_track()
    with col2:
        if st.button("⏯", use_container_width=True):
            current = sp.current_playback()
            if current and current["is_playing"]:
                sp.pause_playback()
            else:
                sp.start_playback()
    with col3:
        if st.button("⏭", use_container_width=True):
            sp.next_track()

def visualizer():
    st.markdown("""
        <style>
        .bar-container {display:flex; justify-content:center; gap:6px; margin:10px 0;}
        .bar {width:4px; height:15px; background:white; border-radius:2px; animation:bounce 1s infinite;}
        .bar:nth-child(2) { animation-delay:0.2s; }
        .bar:nth-child(3) { animation-delay:0.4s; }
        @keyframes bounce {0%,100%{height:10px;}50%{height:30px;}}
        </style>
        <div class="bar-container">
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
        </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Pagina layout
# -----------------------------
st.set_page_config(page_title="Spotify Dashboard", page_icon="🎵", layout="wide")

# Hide Streamlit chrome
st.markdown("""
    <style>
    .block-container { padding: 0; }
    header, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

track = get_current_track()

if track:
    r, g, b = track["dominant_color"]
    bg_color = f"linear-gradient(135deg, rgb({r},{g},{b}), #000000)"
else:
    bg_color = "linear-gradient(135deg, #1DB954, #000000)"

st.markdown(f"""
    <style>
    body {{background: {bg_color};}}
    </style>
""", unsafe_allow_html=True)

# Spotify Section
st.markdown("""
    <div style="text-align:center;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg"
             style="width:100px; margin-bottom:15px;">
    </div>
""", unsafe_allow_html=True)

if track:
    st.markdown(f"""
        <div style="text-align:center; color:white;">
            <img src="{track['cover_url']}" style="width:110px; border-radius:12px; margin-bottom:10px;">
            <div style="font-size:16px; font-weight:bold;">{track['title']} – {track['artist']}</div>
        </div>
    """, unsafe_allow_html=True)

    visualizer()
    media_controls()
else:
    st.markdown("<div style='text-align:center; color:white;'>No track playing</div>", unsafe_allow_html=True)

# Tabs (subpages)
tabs = st.tabs(["🚴 Ritten", "📊 Statistieken", "⚙️ Instellingen"])

with tabs[0]:
    st.write("Hier komt je ritten logboek")

with tabs[1]:
    st.write("Hier komen je statistieken en grafieken")

with tabs[2]:
    st.write("Hier komen je instellingen")

