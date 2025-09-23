import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from PIL import Image
from io import BytesIO
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
    body { 
        background-color: #000; 
        font-family: -apple-system,BlinkMacSystemFont,sans-serif; 
        color: white; 
        margin: 0; 
        padding: 0; 
    }
    
    /* Glazen tegel effect */
    .glass-tile { 
        background: rgba(30,30,30,0.6); 
        backdrop-filter: blur(40px); 
        border-radius: 25px; 
        padding: 20px; 
        margin: 10px 0; 
        box-shadow: 0 15px 35px rgba(0,0,0,0.8); 
        border: 1px solid rgba(255,255,255,0.1);
        width: 100%;
        max-width: 600px;
        overflow: hidden;
    }

    /* Hoes en info */
    .album-art-container { text-align: center; position: relative; }
    .album-art { 
        border-radius: 20px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.7); 
        transition: transform 0.3s;
    }
    .album-art-glow {
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        filter: blur(40px);
        z-index: -1;
        background-size: cover;
        opacity: 0.8;
        border-radius: 20px;
    }
    .track-info { 
        font-size: 24px; 
        font-weight: 700; 
        margin-top: 20px; 
        text-align: center; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
    }
    .artist-info { 
        font-size: 16px; 
        color: #b3b3b3; 
        text-align: center; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
    }

    /* Voortgangsbalk */
    .progress-bar-container { 
        background: rgba(255,255,255,0.1); 
        border-radius: 8px; 
        width: 100%; 
        height: 6px; 
        margin: 20px 0 15px; 
        position: relative;
    }
    .progress-bar { 
        background: #1DB954; 
        height: 100%; 
        border-radius: 8px; 
        transition: width 0.5s linear; 
    }
    .progress-bar-thumb {
        position: absolute;
        right: 0;
        top: 50%;
        transform: translate(50%, -50%);
        width: 12px;
        height: 12px;
        background-color: #fff;
        border-radius: 50%;
        box-shadow: 0 0 10px #1DB954;
    }

    /* Bedieningselementen */
    .controls-container { 
        text-align: center; 
        display: flex; 
        justify-content: space-around; 
        padding: 10px; 
        gap: 20px;
    }
    .controls-container button { 
        background-color: transparent; 
        border: none; 
        width: 70px;
        height: 70px;
        border-radius: 50%; 
        cursor: pointer; 
        transition: background-color 0.2s, transform 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .controls-container button:hover { background-color: rgba(255,255,255,0.1); }
    .controls-container button:active { transform: scale(0.95); }
    .play-button { 
        background-color: #1DB954 !important; 
        box-shadow: 0 0 20px rgba(29, 185, 84, 0.5);
    }
    .play-button:hover { background-color: #1ed760 !important; }

    /* SVG icon styling */
    .icon { width: 32px; height: 32px; fill: white; }
    .icon-play { fill: black; }

    /* Recent afgespeeld sectie */
    .recent-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
    .scrolling-tiles { 
        display: flex; 
        overflow-x: scroll; 
        padding: 5px; 
        -webkit-overflow-scrolling: touch; 
        gap: 15px;
    }
    .scrolling-tiles::-webkit-scrollbar { display: none; }
    .scrolling-tiles div { 
        flex: 0 0 auto; 
        text-align: center; 
        width: 100px;
    }
    .scrolling-tiles img { border-radius: 12px; width: 100px; height: 100px; object-fit: cover; }
    .recent-track-name { 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        color: #b3b3b3; 
        font-size: 12px;
        margin-top: 5px;
    }
    .recent-artist-name { 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        color: #777; 
        font-size: 11px;
    }

    /* Logout knop */
    .logout-button { 
        background-color: rgba(255, 92, 92, 0.7); 
        border: none; 
        color: white; 
        padding: 8px 15px; 
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
        align-items: center;
        width: 100%;
        padding: 20px;
        box-sizing: border-box;
        height: 100vh;
        overflow-y: auto;
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
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        
        # Logout knop
        if st.button("Log uit", key="logout_btn", help="Klik om uit te loggen en de cache te wissen"):
            st.session_state.clear()
            st.rerun()

        # Muziekspeler sectie
        st.markdown('<div class="glass-tile">', unsafe_allow_html=True)
        try:
            current = sp.current_playback()
            
            if current and current.get("item"):
                track = current["item"]["name"]
                artist = ", ".join([a["name"] for a in current["item"]["artists"]])
                cover_url = current["item"]["album"]["images"][0]["url"]
                
                try:
                    response = requests.get(cover_url, timeout=5)
                    response.raise_for_status()
                    img_bytes = BytesIO(response.content)
                    
                    st.markdown("<div class='album-art-container'>", unsafe_allow_html=True)
                    st.image(img_bytes, width=280, output_format="PNG", caption="")
                    st.markdown("</div>", unsafe_allow_html=True)

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
                                <div class='progress-bar-thumb' style='left:{pct}%;'></div>
                            </div>
                        """, unsafe_allow_html=True)

                    # Bedieningsknoppen met SVG
                    st.markdown('<div class="controls-container">', unsafe_allow_html=True)
                    col_a, col_b, col_c = st.columns([1, 1, 1])
                    with col_a:
                        if st.button('<svg xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 13.5v-7l5 3.5-5 3.5z"/></svg>', key="prev_btn", unsafe_allow_html=True): 
                            sp.previous_track()
                    with col_b:
                        if current.get("is_playing"):
                            if st.button('<svg xmlns="http://www.w3.org/2000/svg" class="icon icon-play" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>', key="play_pause_btn", unsafe_allow_html=True):
                                sp.pause_playback()
                        else:
                            if st.button('<svg xmlns="http://www.w3.org/2000/svg" class="icon icon-play" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>', key="play_pause_btn", unsafe_allow_html=True):
                                sp.start_playback()
                    with col_c:
                        if st.button('<svg xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 13.5v-7l5 3.5-5 3.5z"/></svg>', key="next_btn", unsafe_allow_html=True):
                            sp.next_track()
                    st.markdown('</div>', unsafe_allow_html=True)

                except (requests.exceptions.RequestException, IOError) as e:
                    st.error(f"Fout bij het ophalen van de albumhoes: {e}")
            else:
                st.write("Er wordt momenteel geen muziek afgespeeld.")
                st.markdown('<div class="controls-container">', unsafe_allow_html=True)
                col_a, col_b, col_c = st.columns([1, 1, 1])
                with col_a:
                    st.button('<svg xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 13.5v-7l5 3.5-5 3.5z"/></svg>', key="prev_btn", disabled=True, unsafe_allow_html=True)
                with col_b:
                    st.button('<svg xmlns="http://www.w3.org/2000/svg" class="icon icon-play" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>', key="play_pause_btn", unsafe_allow_html=True)
                with col_c:
                    st.button('<svg xmlns="http://www.w3.org/2000/svg" class="icon" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 13.5v-7l5 3.5-5 3.5z"/></svg>', key="next_btn", disabled=True, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Er is een onverwachte fout opgetreden: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Recent afgespeeld sectie
        st.markdown('<div class="glass-tile">', unsafe_allow_html=True)
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
                            <img src="{cover_url}" width="100" class="album-art"><br>
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
