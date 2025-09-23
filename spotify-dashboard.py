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
        st.markdown("<div class='login-prompt'>", unsafe_allow_html=True)
        st.markdown("### 1️⃣ Log in bij Spotify")
        st.markdown(f"[Klik hier om in te loggen bij Spotify]({auth_url})")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='login-prompt'>", unsafe_allow_html=True)
        st.markdown("### 2️⃣ Plak de code uit de URL hier", unsafe_allow_html=True)
        code = st.text_input("", key="auth_code", help="Plak de URL en haal alleen de code eruit. Je vindt die na '?code=' en voor '&state='")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if code:
            try:
                token_info = sp_oauth.get_access_token(code, as_dict=True)
                st.session_state["token_info"] = token_info
                st.rerun()
            except Exception as e:
                st.error(f"Spotify inloggen mislukt. Zorg ervoor dat je alleen de code hebt geplakt. Fout: {e}")
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
    # CSS Styling voor een native CarPlay-look
    # =========================
    st.markdown("""
    <style>
    /* Algemene stijl */
    body { background: #000; font-family: -apple-system,BlinkMacSystemFont,sans-serif; color: white; margin: 0; padding: 0; }
    
    /* Glazen tegel effect */
    .glass-tile { 
        background: rgba(20,20,20,0.6); 
        backdrop-filter: blur(25px); 
        border-radius: 20px; 
        padding: 15px; 
        margin: 5px; 
        box-shadow: 0 5px 20px rgba(0,0,0,0.5); 
        border: 1px solid rgba(255,255,255,0.1);
        width: 100%;
        overflow: hidden;
    }

    /* Hoes en info */
    .album-art-container { text-align: center; }
    .album-art { border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.7); }
    .track-info { font-size: 20px; font-weight: 700; margin-top: 10px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .artist-info { font-size: 14px; color: #b3b3b3; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Voortgangsbalk */
    .progress-bar-container { background: rgba(255,255,255,0.1); border-radius: 8px; width: 100%; height: 5px; margin: 15px 0 10px; }
    .progress-bar { background: #1DB954; height: 100%; border-radius: 8px; transition: width 0.5s; }

    /* Bedieningselementen */
    .controls-container { text-align: center; display: flex; justify-content: space-around; padding: 10px; }
    .controls-container button { 
        background-color: transparent; 
        border: none; 
        color: white; 
        width: 60px;
        height: 60px;
        border-radius: 50%; 
        cursor: pointer; 
        transition: background-color 0.2s, box-shadow 0.2s, transform 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .controls-container button:hover { background-color: rgba(255,255,255,0.1); }
    .controls-container button:active { transform: scale(0.95); box-shadow: inset 0 0 10px rgba(0,0,0,0.3); }
    .controls-container button.play-button { background-color: #1DB954; }
    .controls-container button.play-button:hover { background-color: #1ed760; }
    .controls-container button.play-button:active { transform: scale(0.95); box-shadow: inset 0 0 10px rgba(0,0,0,0.3); }

    /* SVG icon styling */
    .icon { width: 24px; height: 24px; fill: white; }
    .icon-play { fill: black; }

    /* Recent afgespeeld sectie */
    .recent-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
    .scrolling-tiles { display: flex; overflow-x: scroll; padding: 5px; -webkit-overflow-scrolling: touch; }
    .scrolling-tiles::-webkit-scrollbar { display: none; }
    .scrolling-tiles div { 
        margin-right: 15px; 
        flex: 0 0 auto; 
        text-align: center; 
        font-size: 10px; 
        width: 80px;
    }
    .scrolling-tiles img { border-radius: 10px; width: 80px; height: 80px; object-fit: cover; }
    .recent-track-name { 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        color: #b3b3b3; 
        font-size: 11px;
    }
    .recent-artist-name { 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        color: #777; 
        font-size: 10px;
    }

    /* Logout knop */
    .logout-button { 
        background-color: rgba(255, 92, 92, 0.7); 
        border: none; 
        color: white; 
        padding: 5px 10px; 
        border-radius: 10px; 
        cursor: pointer; 
        font-size: 12px; 
        float: right; 
        margin: 5px; 
        transition: background-color 0.3s;
    }
    .logout-button:hover { background-color: rgba(255, 92, 92, 1); }

    /* Algemene lay-out aanpassingen */
    .stApp { background-color: #000; }
    .main-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        width: 100%;
        padding: 20px;
        box-sizing: border-box;
    }
    .music-player-card {
        width: 100%;
        max-width: 600px;
        margin-bottom: 20px;
    }
    .recent-played-card {
        width: 100%;
        max-width: 600px;
    }
    .login-prompt {
        text-align: center;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    sp = get_current_spotify_session()

    if not sp:
        handle_login()
    else:
        # Toon logout knop
        if st.button("Log uit", key="logout_btn", help="Klik om uit te loggen en de cache te wissen"):
            st.session_state.clear()
            st.rerun()

        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        
        # Muziekspeler sectie
        st.markdown('<div class="glass-tile music-player-card">', unsafe_allow_html=True)
        try:
            current = sp.current_playback()
            
            if current and current.get("item"):
                track = current["item"]["name"]
                artist = ", ".join([a["name"] for a in current["item"]["artists"]])
                cover_url = current["item"]["album"]["images"][0]["url"]
                
                try:
                    response = requests.get(cover_url, timeout=5)
                    response.raise_for_status()
                    img = Image.open(BytesIO(response.content))
                    
                    st.columns(3)[1].image(img, width=250, output_format="PNG", caption="")
                    
                    st.markdown(f"<div class='track-info'>{track}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='artist-info'>{artist}</div>", unsafe_allow_html=True)

                    # Voortgangsbalk
                    duration = current["item"]["duration_ms"]
                    progress = current["progress_ms"]
                    if duration > 0:
                        pct = int((progress / duration) * 100)
                        st.markdown(f"""
                            <div class='progress-bar-container'>
                                <div class='progress-bar' style='width:{pct}%;'></div>
                            </div>
                        """, unsafe_allow_html=True)

                    # Bedieningsknoppen
                    col_a, col_b, col_c = st.columns([1, 1, 1])
                    with col_a:
                        if st.button("<<", key="prev_btn"): sp.previous_track()
                    with col_b:
                        if st.button(">", key="play_pause_btn"):
                            if current and current.get("is_playing"):
                                sp.pause_playback()
                            else:
                                sp.start_playback()
                    with col_c:
                        if st.button(">>", key="next_btn"): sp.next_track()
                except (requests.exceptions.RequestException, IOError) as e:
                    st.error(f"Fout bij het ophalen van de albumhoes: {e}")
            else:
                st.write("Er wordt momenteel geen muziek afgespeeld.")
                st.markdown('<div class="controls-container">', unsafe_allow_html=True)
                col_a, col_b, col_c = st.columns([1, 1, 1])
                with col_a:
                    st.button("<<", key="prev_btn", disabled=True)
                with col_b:
                    st.button(">", key="play_pause_btn")
                with col_c:
                    st.button(">>", key="next_btn", disabled=True)
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Er is een onverwachte fout opgetreden: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Recent afgespeeld sectie
        st.markdown('<div class="glass-tile recent-played-card">', unsafe_allow_html=True)
        st.markdown('<div class="recent-header">Recent afgespeeld</div>', unsafe_allow_html=True)
        try:
            recent = sp.current_user_recently_played(limit=6)
            if recent and "items" in recent:
                st.markdown("<div class='scrolling-tiles'>", unsafe_allow_html=True)
                for item in recent["items"]:
                    if "track" in item and "album" in item["track"] and "images" in item["track"]["album"]:
                        t_name = item["track"]["name"]
                        a_name = ", ".join([a["name"] for a in item["track"]["artists"]])
                        cover_url = item["track"]["album"]["images"][2]["url"]
                        st.markdown(f"""
                            <div>
                            <img src="{cover_url}" width="80" class="album-art"><br>
                            <span class="recent-track-name">{t_name}</span><br>
                            <span class="recent-artist-name">{a_name}</span>
                            </div>
                        """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Fout bij het ophalen van recent afgespeelde nummers: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
