import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image, ImageFilter
from io import BytesIO
import numpy as np
import time

# =========================
# Spotify instellingen via st.secrets
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
    st.set_page_config(page_title="Spotify Dashboard", layout="wide")

    # =========================
    # CSS Styling
    # =========================
    st.markdown("""
    <style>
    body { background-color:#0d0d0d; font-family:-apple-system,BlinkMacSystemFont,sans-serif; color:white; }
    .tile { background-color:#121212; border-radius:20px; padding:15px; box-shadow:0 5px 15px rgba(0,0,0,0.5); margin-bottom:15px; }
    .track-info {font-size:20px; font-weight:600; margin-bottom:5px;}
    .artist-info {font-size:14px; color:#b3b3b3; margin-bottom:10px;}
    .controls button {background-color:#1DB954; border:none; color:white; padding:10px 15px; margin:0 5px; border-radius:50px; cursor:pointer; font-size:16px; transition:all 0.2s;}
    .controls button:hover {transform:scale(1.2); box-shadow:0 0 10px #1DB954;}
    .cover-glow {border-radius:15px; box-shadow:0 0 40px rgba(29,185,84,0.7); animation: pulse 2s infinite;}
    @keyframes pulse {0%{box-shadow:0 0 20px rgba(29,185,84,0.5);}50%{box-shadow:0 0 50px rgba(29,185,84,0.9);}100%{box-shadow:0 0 20px rgba(29,185,84,0.5);}}
    .scrolling-tiles {display:flex; overflow-x:auto; padding:5px;}
    .scrolling-tiles div {margin-right:10px; flex:0 0 auto; text-align:center;}
    </style>
    """, unsafe_allow_html=True)

    # =========================
    # Fetch current playback
    # =========================
    current = sp.current_playback()
    col1, col2 = st.columns([1,1])

    with col1:
        if current and current.get("item"):
            track = current["item"]["name"]
            artist = ", ".join([a["name"] for a in current["item"]["artists"]])
            cover_url = current["item"]["album"]["images"][1]["url"]
            response = requests.get(cover_url)
            img = Image.open(BytesIO(response.content)).resize((160,160))
            glow = img.filter(ImageFilter.GaussianBlur(radius=20))

            st.image(glow, width=200)
            st.image(img, width=160)
            st.markdown(f"<div class='track-info'>{track}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='artist-info'>{artist}</div>", unsafe_allow_html=True)

            # Audio visualizer
            bars = np.random.randint(5,40, size=10)
            bar_html = "".join([f"<div style='display:inline-block;width:10px;height:{h}px;margin:1px;background:#1DB954;border-radius:5px;animation:bounce 1s infinite;'></div>" for h in bars])
            st.markdown(f"<div style='margin:10px 0'>{bar_html}</div>", unsafe_allow_html=True)
            st.markdown("<style>@keyframes bounce {0%,100%{transform:scaleY(0.5);}50%{transform:scaleY(1.2);}}</style>", unsafe_allow_html=True)
        else:
            st.write("Geen muziek aan het spelen.")

    with col2:
        st.markdown("<div class='tile' style='text-align:center;'>", unsafe_allow_html=True)
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

        # =========================
        # Recently played compact
        # =========================
        recent = sp.current_user_recently_played(limit=8)
        st.markdown("### 🎵 Recent Geluisterd")
        st.markdown('<div class="scrolling-tiles">', unsafe_allow_html=True)
        for item in recent["items"]:
            t_name = item["track"]["name"]
            a_name = ", ".join([a["name"] for a in item["track"]["artists"]])
            cover_url = item["track"]["album"]["images"][2]["url"]
            st.markdown(f"""
                <div>
                <img src="{cover_url}" width="80" style="border-radius:10px;"><br>
                <span style="color:#b3b3b3;font-size:11px;">{t_name}</span><br>
                <span style="color:#777;font-size:10px;">{a_name}</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # =========================
    # Auto-refresh
    # =========================
    time.sleep(5)
    st.experimental_rerun()
