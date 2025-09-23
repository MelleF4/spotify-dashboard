import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image, ImageFilter
from io import BytesIO
import numpy as np
from streamlit_autorefresh import st_autorefresh

# =========================
# Automatisch verversen elke 5 seconden
# =========================
st_autorefresh(interval=5000, limit=None, key="refresh")

# =========================
# Spotify instellingen via st.secrets
# =========================
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]
    SCOPE = "user-read-playback-state,user-read-currently-playing,user-read-recently-played,user-top-read"
except KeyError as e:
    st.error(f"Fout: Vereiste geheime sleutel ontbreekt: {e}. Voeg deze toe aan je Streamlit geheimen.")
    st.stop()

# =========================
# Spotify authenticatie flow
# =========================
def get_spotify_oauth():
    """Initialiseert en retourneert het SpotifyOAuth object."""
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=".spotifycache"
    )

def handle_login():
    """Behandelt het Spotify inlogproces."""
    if "token_info" not in st.session_state or not st.session_state["token_info"]:
        sp_oauth = get_spotify_oauth()
        auth_url = sp_oauth.get_authorize_url()
        st.markdown("### 1️⃣ Log in bij Spotify")
        st.markdown(f"[Klik hier om in te loggen bij Spotify]({auth_url})")
        code = st.text_input("### 2️⃣ Plak de code uit de URL hier", key="auth_code")
        if code:
            try:
                token_info = sp_oauth.get_access_token(code, as_dict=True)
                st.session_state["token_info"] = token_info
                st.rerun()
            except Exception as e:
                st.error(f"Spotify inloggen mislukt: {e}")
                st.session_state["token_info"] = None

def get_current_spotify_session():
    """Retourneert een Spotipy client als de gebruiker is ingelogd, anders None."""
    if "token_info" in st.session_state and st.session_state["token_info"]:
        sp_oauth = get_spotify_oauth()
        token_info = sp_oauth.validate_token(st.session_state["token_info"])
        if token_info:
            return spotipy.Spotify(auth=token_info["access_token"])
        else:
            st.session_state["token_info"] = None
            st.rerun()
    return None

def main():
    """Hoofdlogica van de applicatie."""
    st.set_page_config(page_title="CarPlay Spotify", layout="wide")

    # =========================
    # CSS Styling voor een compacte CarPlay-look
    # =========================
    st.markdown("""
    <style>
    body { background: #000; font-family: -apple-system,BlinkMacSystemFont,sans-serif; color: white; margin: 0; padding: 0; }
    .glass-tile { background: rgba(20,20,20,0.6); backdrop-filter: blur(25px); border-radius: 20px; padding: 10px; margin: 5px; box-shadow: 0 5px 20px rgba(0,0,0,0.5); }
    .track-info { font-size: 18px; font-weight: 700; margin-top: 5px; }
    .artist-info { font-size: 13px; color: #b3b3b3; margin-bottom: 5px; }
    .controls-container { text-align: center; }
    .controls button { background-color: #1DB954; border: none; color: white; padding: 8px 16px; margin: 0 4px; border-radius: 40px; cursor: pointer; font-size: 14px; transition: all 0.25s; }
    .controls button:hover { transform: scale(1.1); box-shadow: 0 0 10px #1DB954; }
    .visualizer div { display: inline-block; width: 6px; margin: 1px; background: #1DB954; border-radius: 3px; animation: bounce 1s infinite; }
    @keyframes bounce { 0%, 100% { transform: scaleY(0.5); } 50% { transform: scaleY(1.2); } }
    .scrolling-tiles { display: flex; overflow-x: auto; padding: 5px; }
    .scrolling-tiles div { margin-right: 8px; flex: 0 0 auto; text-align: center; font-size: 10px; }
    .scrolling-tiles img { border-radius: 10px; }
    .progress-bar-container { background: rgba(255,255,255,0.1); border-radius: 8px; width: 100%; height: 5px; margin: 5px 0; }
    .progress-bar { background: #1DB954; height: 100%; border-radius: 8px; transition: width 0.5s; }
    .logout-button { background-color: rgba(255, 92, 92, 0.5); border: none; color: white; padding: 5px 10px; border-radius: 10px; cursor: pointer; font-size: 12px; float: right; margin: 5px; }
    </style>
    """, unsafe_allow_html=True)

    sp = get_current_spotify_session()

    if not sp:
        handle_login()
    else:
        # Gebruiker is geauthenticeerd, toon het dashboard
        if st.button("Log uit", key="logout_btn", help="Klik om uit te loggen en de cache te wissen"):
            st.session_state.clear()
            st.rerun()

        st.title("CarPlay Spotify")

        col1, col2 = st.columns([1, 1])

        with col1:
            try:
                current = sp.current_playback()
                if current and current.get("item"):
                    track = current["item"]["name"]
                    artist = ", ".join([a["name"] for a in current["item"]["artists"]])
                    cover_url = current["item"]["album"]["images"][0]["url"]
                    
                    response = requests.get(cover_url)
                    response.raise_for_status() # Roept een fout op bij slechte respons
                    
                    img = Image.open(BytesIO(response.content)).resize((200, 200))
                    st.image(img, width=180, caption=f"{track} by {artist}")

                    st.markdown(f"<div class='track-info'>{track}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='artist-info'>{artist}</div>", unsafe_allow_html=True)

                    # Voortgangsbalk
                    duration = current["item"]["duration_ms"]
                    progress = current["progress_ms"]
                    pct = int((progress / duration) * 100)
                    st.markdown(f"""
                        <div class='progress-bar-container'>
                            <div class='progress-bar' style='width:{pct}%;'></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Audiovisualizer (alleen esthetisch)
                    bars = np.random.randint(5, 45, size=20)
                    bar_html = "".join([f"<div style='height:{h}px'></div>" for h in bars])
                    st.markdown(f"<div class='visualizer'>{bar_html}</div>", unsafe_allow_html=True)

                else:
                    st.write("Er wordt momenteel geen muziek afgespeeld.")
            except requests.exceptions.RequestException as e:
                st.error(f"Fout bij het ophalen van de albumhoes: {e}")
            except Exception as e:
                st.error(f"Er is een onverwachte fout opgetreden: {e}")

        with col2:
            st.markdown('<div class="glass-tile controls-container">', unsafe_allow_html=True)
            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_a:
                if st.button("⏮️", key="prev_btn"): sp.previous_track()
            with col_b:
                if st.button("⏯️", key="play_pause_btn"):
                    if current and current["is_playing"]:
                        sp.pause_playback()
                    else:
                        sp.start_playback()
            with col_c:
                if st.button("⏭️", key="next_btn"): sp.next_track()
            st.markdown('</div>', unsafe_allow_html=True)

            # Recent afgespeeld
            try:
                recent = sp.current_user_recently_played(limit=6)
                st.markdown("<div class='glass-tile'><h3>Recent afgespeeld</h3><div class='scrolling-tiles'>", unsafe_allow_html=True)
                for item in recent["items"]:
                    t_name = item["track"]["name"]
                    a_name = ", ".join([a["name"] for a in item["track"]["artists"]])
                    cover_url = item["track"]["album"]["images"][2]["url"]
                    st.markdown(f"""
                        <div>
                        <img src="{cover_url}" width="70" style="border-radius:10px;"><br>
                        <span style="color:#b3b3b3;font-size:10px;">{t_name}</span><br>
                        <span style="color:#777;font-size:9px;">{a_name}</span>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div></div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Fout bij het ophalen van recent afgespeelde nummers: {e}")

if __name__ == "__main__":
    main()
