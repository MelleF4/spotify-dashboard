import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image, ImageFilter
from io import BytesIO
import numpy as np
from streamlit.components.v1 import html

# =========================
# Spotify instellingen
# =========================
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
SCOPE = "user-read-playback-state,user-modify-playback-state,user-read-currently-playing"

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotifycache"
)

# =========================
# Spotify login handmatig
# =========================
if "token_info" not in st.session_state:
    st.session_state["token_info"] = None

if st.session_state["token_info"] is None:
    auth_url = sp_oauth.get_authorize_url()
    st.markdown("### 1️⃣ Log in bij Spotify")
    st.markdown(f"[Klik hier om in te loggen bij Spotify]({auth_url})")
    code = st.text_input("### 2️⃣ Plak hier de code uit de URL")
    if code:
        try:
            token_info = sp_oauth.get_access_token(code, as_dict=True)
            st.session_state["token_info"] = token_info
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Spotify login mislukt: {e}")

# =========================
# Spotify dashboard
# =========================
if st.session_state["token_info"]:
    token_info = sp_oauth.validate_token(st.session_state["token_info"])
    if not token_info:
        st.session_state["token_info"] = None
        st.experimental_rerun()

    sp = spotipy.Spotify(auth=token_info["access_token"])
    st.set_page_config(page_title="CarPlay Dashboard", layout="wide")

    st.markdown("""
    <style>
    body { background-color: #0d0d0d; font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: white;}
    .tile { background-color:#121212; border-radius:25px; padding:20px; margin-bottom:15px; box-shadow:0 8px 20px rgba(0,0,0,0.5);}
    .spotify-logo {width:120px; margin-bottom:10px;}
    .track-info {font-size:20px; font-weight:600;}
    .artist-info {font-size:14px; color:#b3b3b3;}
    .controls button {background-color:#1DB954; border:none; color:white; padding:12px 20px; margin:0 10px; border-radius:50px; cursor:pointer; font-size:18px; transition:all 0.2s;}
    .controls button:hover {transform:scale(1.2); box-shadow:0 0 15px #1DB954;}
    .cover-glow {border-radius:15px; box-shadow:0 0 40px rgba(29,185,84,0.7); animation: pulse 2s infinite;}
    @keyframes pulse {0% {box-shadow:0 0 20px rgba(29,185,84,0.5);} 50% {box-shadow:0 0 50px rgba(29,185,84,0.9);} 100% {box-shadow:0 0 20px rgba(29,185,84,0.5);}}
    </style>
    """, unsafe_allow_html=True)

    # Spotify tile
    with st.container():
        st.markdown('<div class="tile" style="text-align:center;">', unsafe_allow_html=True)
        st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_White.png", width=120)
        current = sp.current_playback()
        if current and current.get("item"):
            track = current["item"]["name"]
            artist = ", ".join([a["name"] for a in current["item"]["artists"]])
            cover_url = current["item"]["album"]["images"][1]["url"]
            response = requests.get(cover_url)
            img = Image.open(BytesIO(response.content)).resize((140,140))
            # glow effect
            glow = img.filter(ImageFilter.GaussianBlur(radius=15))
            st.image(glow, width=150)
            st.image(img, width=140)
            st.markdown(f"<div class='track-info'>{track}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='artist-info'>{artist}</div>", unsafe_allow_html=True)

            # Simpele audio-visualizer (fake)
            bars = np.random.randint(5,50, size=10)
            bar_html = "".join([f"<div style='display:inline-block;width:10px;height:{h}px;margin:2px;background:#1DB954;border-radius:5px;animation: bounce 1s infinite;'></div>" for h in bars])
            st.markdown(f"<div style='margin:20px 0'>{bar_html}</div>", unsafe_allow_html=True)
            st.markdown("""
            <style>
            @keyframes bounce {0%,100%{transform:scaleY(0.5);}50%{transform:scaleY(1.2);}}
            </style>
            """, unsafe_allow_html=True)

            # Media controls
            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                if st.button("⏮️"): sp.previous_track()
            with col2:
                if st.button("⏯️"):
                    if current["is_playing"]: sp.pause_playback()
                    else: sp.start_playback()
            with col3:
                if st.button("⏭️"): sp.next_track()
        else:
            st.write("Geen muziek aan het spelen.")
        st.markdown('</div>', unsafe_allow_html=True)


