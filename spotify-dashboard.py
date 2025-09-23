import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import folium_static
import folium

# =========================
# Automatisch verversen elke 5 seconden om de Spotify status te updaten
# =========================
st_autorefresh(interval=5000, limit=None, key="refresh")

# =========================
# Spotify instellingen vanuit st.secrets
# Zorg ervoor dat deze keys in je .streamlit/secrets.toml bestand staan
# =========================
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]
    SCOPE = "user-read-playback-state,user-read-currently-playing,user-read-recently-played,user-top-read,user-modify-playback-state"
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
        
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.markdown("<div class='glass-tile login-box'>", unsafe_allow_html=True)
        st.markdown("""
            <div style="text-align: center;">
                <svg viewBox="0 0 167.5 167.5" xmlns="http://www.w3.org/2000/svg" style="width: 80px; height: 80px;">
                    <title>Spotify Logo</title>
                    <path fill="#1DB954" d="M83.75 0C37.5 0 0 37.5 0 83.75c0 46.25 37.5 83.75 83.75 83.75 46.25 0 83.75-37.5 83.75-83.75C167.5 37.5 130 0 83.75 0zm37.5 120.5c-2.5 4.5-8.5 6-13 3.5-16-9.5-35.5-11.5-56.5-6.5-5.5 1.5-11.5-1.5-13-7s1.5-11.5 7-13c24.5-6 48.5-3.5 67 8.5 4.5 2.5 5.5 8.5 3 13zm8.5-23.5c-3 5-10 6.5-15 3.5-19.5-12-49.5-15.5-67.5-10.5-6.5 1.5-13.5-2-15-8.5-1.5-6.5 2-13.5 8.5-15 23-6.5 57.5-2.5 80 14 5.5 3 7 10 3.5 15zm0-23.5c-3-5.5-11.5-7.5-17.5-4-26 15.5-65 15-88.5-7.5-5.5-5.5-5.5-14.5 0-20 5.5-5.5 14.5-5.5 20 0 25 24 64 24.5 85 9.5 5-3.5 7-11.5 3.5-17z"/>
                </svg>
                <h1 style="color: black; font-size: 24px;">Log in bij Spotify</h1>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"[Klik hier om in te loggen]({auth_url})", unsafe_allow_html=True)
        code = st.text_input("Plak de code uit de URL hieronder", key="auth_code")
        
        if code:
            try:
                token_info = sp_oauth.get_access_token(code, as_dict=True)
                st.session_state["token_info"] = token_info
                st.rerun()
            except Exception as e:
                st.error(f"Spotify inloggen mislukt. Zorg ervoor dat je alleen de code hebt geplakt. Fout: {e}")
                st.session_state["token_info"] = None
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


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
    st.set_page_config(page_title="CarPlay Fiets Dashboard", layout="wide")

    # =========================
    # CSS Styling voor een native CarPlay-look
    # =========================
    st.markdown("""
    <style>
    /* Algemene stijl - Lichte modus */
    body { 
        background-color: #f0f0f5; 
        font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
        color: black; 
        margin: 0; 
        padding: 0; 
    }
    
    .stApp { background-color: #f0f0f5; }
    
    .main-container {
        display: flex;
        flex-direction: row;
        justify-content: center;
        align-items: flex-start;
        gap: 20px;
        padding: 20px;
        box-sizing: border-box;
        height: 100vh;
        overflow-y: auto;
    }
    
    /* Glazen tegel effect voor lichte modus */
    .glass-tile { 
        background: rgba(255, 255, 255, 0.7); 
        backdrop-filter: blur(40px); 
        border-radius: 25px; 
        padding: 20px; 
        box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1); 
        border: 1px solid rgba(0, 0, 0, 0.2);
        width: 100%;
        max-width: 600px;
        overflow: hidden;
    }

    /* Spotify speler en info */
    .player-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 20px;
    }
    .album-art-large {
        border-radius: 12px;
        width: 100%;
        max-width: 300px;
        height: auto;
        object-fit: cover;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .track-info-large {
        font-size: 24px;
        font-weight: 700;
        color: #222;
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        margin-bottom: 0;
    }
    .artist-info-large {
        font-size: 18px; 
        color: #666; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis;
        margin-top: 5px;
    }

    /* Bedieningsknoppen */
    .controls-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 25px;
        margin-top: 15px;
    }
    .controls-container .stButton > button {
        background-color: rgba(255, 255, 255, 0.5);
        border: none;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        cursor: pointer;
        transition: background-color 0.2s, transform 0.2s;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        color: black;
        font-size: 24px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .controls-container .stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.8);
    }
    .controls-container .stButton > button:active {
        transform: scale(0.95);
        box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.15);
    }

    .play-btn > button {
        background-color: #1DB954 !important;
        box-shadow: 0 0 10px rgba(29, 185, 84, 0.5) !important;
        color: white !important;
    }
    .play-btn > button:hover {
        background-color: #1ed760 !important;
    }
    
    /* Vorige knop SVG (nu zwart) */
    .prev-btn > button {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'%3E%3Cpath d='M6 6h2v12H6zm3.5 6l8.5 6V6z'/%3E%3C/svg%3E");
    }

    /* Volgende knop SVG (nu zwart) */
    .next-btn > button {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'%3E%3Cpath d='M16 18h2V6h-2zM6 18V6l8.5 6z'/%3E%3C/svg%3E");
    }

    /* Pauze knop SVG (nu zwart) */
    .pause-btn > button {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'%3E%3Cpath d='M6 19h4V5H6v14zm8-14v14h4V5h-4z'/%3E%3C/svg%3E");
    }

    /* Play knop SVG (nu wit) */
    .play-btn > button {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'%3E%3Cpath d='M8 5v14l11-7z'/%3E%3C/svg%3E") !important;
    }
    
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        width: 100vw;
    }

    .login-box {
        text-align: center;
        padding: 40px;
    }
    </style>
    """, unsafe_allow_html=True)

    sp = get_current_spotify_session()

    if not sp:
        handle_login()
    else:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        
        # Kaart Sectie
        with st.container():
            st.markdown('<div class="glass-tile map-container">', unsafe_allow_html=True)
            st.markdown("## 🗺️ Kaart", unsafe_allow_html=True)
            
            m = folium.Map(location=[52.1326, 5.2913], zoom_start=8, tiles="OpenStreetMap", width="100%", height="100%")
            folium_static(m, width=600, height=400)
            
            st.markdown("</div>", unsafe_allow_html=True)

        # Spotify Speler Sectie
        with st.container():
            st.markdown('<div class="glass-tile player-container">', unsafe_allow_html=True)
            
            st.markdown("## 🎵 Muziek", unsafe_allow_html=True)

            try:
                current = sp.current_playback()
                
                if current and current.get("item"):
                    cover_url = current["item"]["album"]["images"][1]["url"]
                    try:
                        response = requests.get(cover_url, timeout=5)
                        response.raise_for_status()
                        img_bytes = BytesIO(response.content)
                        st.image(img_bytes, use_column_width=True, output_format="PNG")
                    except (requests.exceptions.RequestException, IOError):
                        st.image("https://placehold.co/300x300/333333/FFFFFF?text=Spotify", use_column_width=True, output_format="PNG")

                    track = current["item"]["name"]
                    artist = ", ".join([a["name"] for a in current["item"]["artists"]])
                    st.markdown(f"<p class='track-info-large'>{track}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p class='artist-info-large'>{artist}</p>", unsafe_allow_html=True)

                else:
                    st.image("https://placehold.co/300x300/E0E0E0/444444?text=Geen+muziek", use_column_width=True, output_format="PNG")
                    st.markdown("<p class='track-info-large'>Niet aan het afspelen</p>", unsafe_allow_html=True)
                    st.markdown("<p class='artist-info-large'>Log in en speel muziek af om te beginnen</p>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Er is een onverwachte fout opgetreden: {e}")

            # Bedieningsknoppen
            col_a, col_b, col_c = st.columns([1, 1, 1])
            
            with col_a:
                if st.button("<<", key="prev_btn", help="Vorige nummer"):
                    sp.previous_track()
            with col_b:
                if current and current.get("is_playing"):
                    if st.button("||", key="pause_btn", help="Pauze"):
                        sp.pause_playback()
                else:
                    if st.button(">", key="play_btn", help="Speel af"):
                        sp.start_playback()
            with col_c:
                if st.button(">>", key="next_btn", help="Volgende nummer"):
                    sp.next_track()
            
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
        
        # Voeg de CSS-klassen toe aan de knoppen
        st.markdown("""
            <script>
            document.addEventListener("DOMContentLoaded", function() {
                const playBtn = document.querySelector('[data-testid="stButton"] button[title="Speel af"]');
                if (playBtn) playBtn.classList.add("play-btn");
                const pauseBtn = document.querySelector('[data-testid="stButton"] button[title="Pauze"]');
                if (pauseBtn) pauseBtn.classList.add("pause-btn");
            });
            </script>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
