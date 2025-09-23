import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image, ImageFilter
from io import BytesIO
import numpy as np
from streamlit_autorefresh import st_autorefresh

# =========================
# Auto-refresh elke 5 seconden
# =========================
st_autorefresh(interval=5000, limit=None, key="refresh")

# =========================
# Spotify instellingen via st.secrets
# =========================
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
SCOPE = "user-read-playback-state,user-read-currently-playing,user-read-recently-played,user-top-read"

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotifycache"
)

# =========================
# Spotify login
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
# Dashboard
# =========================
if st.session_state["token_info"]:
    token_info = sp_oauth.validate_token(st.session_state["token_info"])
    if not token_info:
        st.session_state["token_info"] = None
        st.experimental_rerun()

    sp = spotipy.Spotify(auth=token_info["access_token"])
    st.set_page_config(page_title="CarPlay Spotify", layout="wide")

    # =========================
    # CSS Styling - CarPlay look
    # =========================
    st.markdown("""
    <style>
    body {
        background: #000;
        font-family: -apple-system,BlinkMacSystemFont,sans-serif;
        color:white;
        margin:0; padding:0;
    }
    .glass-tile {
        background: rgba(20,20,20,0.6);
        backdrop-filter: blur(25px);
        border-radius: 25px;
        padding: 15px;
        margin: 10px;
        box-shadow:0 8px 30px rgba(0,0,0,0.7);
    }
    .track-info { font-size:24px; font-weight:700; margin-top:10px;}
    .artist-info { font-size:16px; color:#b3b3b3; margin-bottom:10px;}
    .controls button {
        background-color:#1DB954;
        border:none;
        color:white;
        padding:12px 25px;
        margin:0 3px;
        border-radius:50px;
        cursor:pointer;
        font-size:18px;
        transition: all 0.25s;
    }
    .controls button:hover {
        transform:scale(1.2);
        box-shadow:0 0 20px #1DB954;
    }
    .visualizer div {
        display:inline-block;
        width:10px;
        margin:1px;
        background:#1DB954;
        border-radius:5px;
        animation:bounce 1s infinite;
    }
    @keyframes bounce {
        0%,100% {transform:scaleY(0.5);}
        50% {transform:scaleY(1.2);}
    }
    .scrolling-tiles { display:flex; overflow-x:auto; padding:10px; }
    .scrolling-tiles div { margin-right:10px; flex:0 0 auto; text-align:center;}
    .progress-bar-container {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        width: 100%;
        height: 8px;
        margin:10px 0;
    }
    .progress-bar {
        background:#1DB954;
        height: 100%;
        border-radius:10px;
        transition: width 0.5s;
    }
    </style>
    """, unsafe_allow_html=True)

    # =========================
    # Fetch current playback
    # =========================
    current = sp.current_playback()
    col1, col2 = st.columns([1,1])

    # =========================
    # Left Panel - Album Cover, Track, Visualizer
    # =========================
    with col1:
        if current and current.get("item"):
            track = current["item"]["name"]
            artist = ", ".join([a["name"] for a in current["item"]["artists"]])
            cover_url = current["item"]["album"]["images"][0]["url"]
            response = requests.get(cover_url)
            img = Image.open(BytesIO(response.content)).resize((220,220))
            glow = img.filter(ImageFilter.GaussianBlur(radius=30))

            st.image(glow, width=360)
            st.image(img, width=220)
            st.markdown(f"<div class='track-info'>{track}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='artist-info'>{artist}</div>", unsafe_allow_html=True)

            # Progress bar
            duration = current["item"]["duration_ms"]
            progress = current["progress_ms"]
            pct = int((progress/duration)*100)
            st.markdown(f"""
                <div class='progress-bar-container'>
                    <div class='progress-bar' style='width:{pct}%;'></div>
                </div>
            """, unsafe_allow_html=True)

            # Audio visualizer
            bars = np.random.randint(5,45, size=20)
            bar_html = "".join([f"<div style='height:{h}px'></div>" for h in bars])
            st.markdown(f"<div class='visualizer'>{bar_html}</div>", unsafe_allow_html=True)
        else:
            st.write("Geen muziek aan het spelen.")

    # =========================
    # Right Panel - Controls + Recently Played
    # =========================
    with col2:
        st.markdown('<div class="glass-tile" style="text-align:center;">', unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([1,1,1])
        with col_a:
            if st.button("⏮️"): sp.previous_track()
        with col_b:
            if st.button("⏯️"):
                if current and current["is_playing"]:
                    sp.pause_playback()
                else:
                    sp.start_playback()
        with col_c:
            if st.button("⏭️"): sp.next_track()
        st.markdown('</div>', unsafe_allow_html=True)

        # Recently Played
        recent = sp.current_user_recently_played(limit=6)
        st.markdown("<div class='glass-tile'><h3>Recently Played</h3><div class='scrolling-tiles'>", unsafe_allow_html=True)
        for item in recent["items"]:
            t_name = item["track"]["name"]
            a_name = ", ".join([a["name"] for a in item["track"]["artists"]])
            cover_url = item["track"]["album"]["images"][2]["url"]
            st.markdown(f"""
                <div>
                <img src="{cover_url}" width="80" style="border-radius:15px;"><br>
                <span style="color:#b3b3b3;font-size:11px;">{t_name}</span><br>
                <span style="color:#777;font-size:10px;">{a_name}</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)



