import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO
import numpy as np
import time

# =========================
# Spotify OAuth via st.secrets
# =========================
sp_oauth = SpotifyOAuth(
    client_id=st.secrets["CLIENT_ID"],
    client_secret=st.secrets["CLIENT_SECRET"],
    redirect_uri=st.secrets["REDIRECT_URI"],
    scope="user-read-playback-state user-read-currently-playing user-read-recently-played user-top-read",
    cache_path=".spotifycache"
)

# =========================
# Login flow
# =========================
if "token_info" not in st.session_state:
    st.session_state["token_info"] = None

if st.session_state["token_info"] is None:
    auth_url = sp_oauth.get_authorize_url()
    st.markdown("### 🔑 Log in bij Spotify")
    st.markdown(f"[Klik hier om in te loggen]({auth_url})")
    code = st.text_input("Plak hier de code uit de URL")
    if code:
        try:
            token_info = sp_oauth.get_access_token(code, as_dict=True)
            st.session_state["token_info"] = token_info
            st.experimental_rerun()
        except:
            st.error("Login mislukt!")

# =========================
# Dashboard
# =========================
if st.session_state["token_info"]:
    token_info = sp_oauth.validate_token(st.session_state["token_info"])
    if not token_info:
        st.session_state["token_info"] = None
        st.experimental_rerun()
    sp = spotipy.Spotify(auth=token_info["access_token"])
    st.set_page_config(page_title="🎶 My Spotify CarPlay", layout="wide")

    # =========================
    # Styling
    # =========================
    st.markdown("""
    <style>
    body {background: linear-gradient(120deg,#0d0d0d,#1a1a1a); color:white; font-family: 'Segoe UI', sans-serif;}
    .cover-container {position: relative; display:inline-block;}
    .cover-glow {border-radius:25px; box-shadow:0 0 70px rgba(29,185,84,0.8); animation:pulse 3s infinite;}
    @keyframes pulse {0%{box-shadow:0 0 20px rgba(29,185,84,0.4);}50%{box-shadow:0 0 70px rgba(29,185,84,1);}100%{box-shadow:0 0 20px rgba(29,185,84,0.4);}}
    .track-title {font-size:30px; font-weight:bold; margin-top:15px;}
    .track-artist {font-size:18px; color:#a3a3a3; margin-bottom:10px;}
    .controls button {background:#1DB954;border:none;color:white;padding:12px 18px;margin:0 5px;border-radius:50px;font-size:20px;cursor:pointer;transition:0.2s;}
    .controls button:hover {transform:scale(1.3); box-shadow:0 0 20px #1DB954;}
    .scroll-container {display:flex; overflow-x:auto; padding:15px;}
    .scroll-item {margin-right:12px; flex:0 0 auto; text-align:center;}
    .scroll-item img {border-radius:15px;}
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
        glow = img.filter(ImageFilter.GaussianBlur(radius=25))
        enhancer = ImageEnhance.Brightness(glow)
        glow = enhancer.enhance(0.5)

        col1, col2 = st.columns([2,1])
        with col1:
            st.image(glow, width=260, output_format="PNG", caption=None)
            st.image(img, width=220)
            st.markdown(f"<div class='track-title'>{track}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='track-artist'>{artist}</div>", unsafe_allow_html=True)

            # Simpele visualizer
            bars = np.random.randint(5,60, size=15)
            bar_html = "".join([f"<div style='display:inline-block;width:12px;height:{h}px;margin:2px;background:#1DB954;border-radius:5px;animation:bounce 1s infinite;'></div>" for h in bars])
            st.markdown(f"<div style='margin:15px 0'>{bar_html}</div>", unsafe_allow_html=True)
            st.markdown("<style>@keyframes bounce{0%,100%{transform:scaleY(0.5);}50%{transform:scaleY(1.2);}}</style>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='controls'>", unsafe_allow_html=True)
            if st.button("⏮️"): sp.previous_track()
            if st.button("⏯️"): 
                if current["is_playing"]: sp.pause_playback()
                else: sp.start_playback()
            if st.button("⏭️"): sp.next_track()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================
        # Recently Played
        # =========================
        recent = sp.current_user_recently_played(limit=8)
        st.markdown("### 🔄 Recently Played")
        st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
        for item in recent["items"]:
            tname = item["track"]["name"]
            aname = ", ".join([a["name"] for a in item["track"]["artists"]])
            cover = item["track"]["album"]["images"][2]["url"]
            st.markdown(f"""
                <div class='scroll-item'>
                    <img src='{cover}' width='90'><br>
                    <span style='color:#b3b3b3;font-size:12px;'>{tname}</span><br>
                    <span style='color:#888;font-size:10px;'>{aname}</span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.write("Geen muziek aan het spelen momenteel.")

    # =========================
    # Auto-refresh
    # =========================
    time.sleep(5)
    st.experimental_rerun()
