import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image, ImageFilter
from io import BytesIO
import numpy as np
import time
from streamlit.components.v1 import html

# =========================
# Spotify instellingen
# =========================
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
SCOPE = "user-read-playback-state,user-modify-playback-state,user-read-currently-playing,user-read-recently-played,user-top-read"

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotifycache"
)

# =========================
# Login
# =========================
if "token_info" not in st.session_state:
    st.session_state["token_info"] = None

if st.session_state["token_info"] is None:
    auth_url = sp_oauth.get_authorize_url()
    st.markdown("### 🎧 Log in bij Spotify")
    st.markdown(f"[Klik hier om in te loggen]({auth_url})")
    code = st.text_input("Plak hier de code uit de URL")
    if code:
        try:
            token_info = sp_oauth.get_access_token(code, as_dict=True)
            st.session_state["token_info"] = token_info
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Login mislukt: {e}")

# =========================
# Dashboard
# =========================
if st.session_state["token_info"]:
    token_info = sp_oauth.validate_token(st.session_state["token_info"])
    if not token_info:
        st.session_state["token_info"] = None
        st.experimental_rerun()

    sp = spotipy.Spotify(auth=token_info["access_token"])
    st.set_page_config(page_title="Spotify CarPlay Dashboard", layout="wide")

    # =========================
    # CSS Styling
    # =========================
    st.markdown("""
    <style>
    body {background: linear-gradient(to bottom, #0d0d0d, #111111); color: white; font-family: -apple-system,BlinkMacSystemFont,sans-serif;}
    .cover-glow {border-radius:20px; box-shadow:0 0 60px rgba(29,185,84,0.7); animation:pulse 2s infinite;}
    @keyframes pulse {0%{box-shadow:0 0 20px rgba(29,185,84,0.5);}50%{box-shadow:0 0 60px rgba(29,185,84,0.9);}100%{box-shadow:0 0 20px rgba(29,185,84,0.5);}}
    .track-title {font-size:28px; font-weight:700; margin-top:10px;}
    .track-artist {font-size:18px; color:#b3b3b3;}
    .controls button {background-color:#1DB954; border:none; color:white; padding:15px 22px; margin:0 8px; border-radius:50px; cursor:pointer; font-size:22px; transition:all 0.2s;}
    .controls button:hover {transform:scale(1.3); box-shadow:0 0 20px #1DB954;}
    .scrolling-tiles {display:flex; overflow-x:auto; padding:10px;}
    .scrolling-tiles div {margin-right:15px; flex:0 0 auto; text-align:center;}
    .tile-title {font-size:12px; color:#b3b3b3; margin-top:3px;}
    .tile-artist {font-size:10px; color:#777;}
    </style>
    """, unsafe_allow_html=True)

    # =========================
    # Huidige track
    # =========================
    current = sp.current_playback()
    if current and current.get("item"):
        track = current["item"]["name"]
        artist = ", ".join([a["name"] for a in current["item"]["artists"]])
        cover_url = current["item"]["album"]["images"][1]["url"]
        response = requests.get(cover_url)
        img = Image.open(BytesIO(response.content)).resize((220,220))
        glow = img.filter(ImageFilter.GaussianBlur(radius=30))

        st.markdown('<div style="text-align:center;">', unsafe_allow_html=True)
        st.image(glow, width=280)
        st.image(img, width=220, use_column_width=False)
        st.markdown(f"<div class='track-title'>{track}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='track-artist'>{artist}</div>", unsafe_allow_html=True)

        # Horizontale audio visualizer
        bars = np.random.randint(5,50, size=20)
        bar_html = "".join([f"<div style='display:inline-block;width:10px;height:{h}px;margin:2px;background:#1DB954;border-radius:5px; animation:bounce 1s infinite;'></div>" for h in bars])
        st.markdown(f"<div style='margin:15px 0'>{bar_html}</div>", unsafe_allow_html=True)
        st.markdown("<style>@keyframes bounce {0%,100%{transform:scaleY(0.5);}50%{transform:scaleY(1.5);}}</style>", unsafe_allow_html=True)

        # Media controls
        st.markdown('<div class="controls" style="text-align:center;margin-bottom:20px;">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button("⏮️ Vorige"): sp.previous_track()
        with col2:
            if st.button("⏯️ Play/Pause"):
                if current["is_playing"]: sp.pause_playback()
                else: sp.start_playback()
        with col3:
            if st.button("⏭️ Volgende"): sp.next_track()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.write("Geen muziek aan het spelen.")

    # =========================
    # Recently Played
    # =========================
    recent = sp.current_user_recently_played(limit=8)
    st.markdown("### 🎵 Recently Played")
    st.markdown('<div class="scrolling-tiles">', unsafe_allow_html=True)
    for item in recent["items"]:
        t_name = item["track"]["name"]
        a_name = ", ".join([a["name"] for a in item["track"]["artists"]])
        cover_url = item["track"]["album"]["images"][2]["url"]
        st.markdown(f"""
            <div>
            <img src="{cover_url}" width="90" style="border-radius:15px;"><br>
            <div class="tile-title">{t_name}</div>
            <div class="tile-artist">{a_name}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # =========================
    # Top Tracks
    # =========================
    top_tracks = sp.current_user_top_tracks(limit=6, time_range="short_term")
    st.markdown("### ⭐ Top Tracks")
    st.markdown('<div class="scrolling-tiles">', unsafe_allow_html=True)
    for item in top_tracks["items"]:
        t_name = item["name"]
        a_name = ", ".join([a["name"] for a in item["artists"]])
        cover_url = item["album"]["images"][2]["url"]
        st.markdown(f"""
            <div>
            <img src="{cover_url}" width="90" style="border-radius:15px;"><br>
            <div class="tile-title">{t_name}</div>
            <div class="tile-artist">{a_name}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # =========================
    # Auto-refresh
    # =========================
    time.sleep(5)
    st.experimental_rerun()
