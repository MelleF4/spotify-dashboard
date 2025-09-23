import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageOps, ImageFilter
import requests
from io import BytesIO
import base64

# Config
st.set_page_config(page_title="CarPlay Spotify", layout="wide")

# Secrets ophalen
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URL"]
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

# Spotify auth
sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        redirect_uri=REDIRECT_URI,
                        scope=SCOPE)

token_info = st.session_state.get("token_info", None)

if not token_info:
    auth_url = sp_oauth.get_authorize_url()
    st.markdown(f"### 🔑 [Login met Spotify]({auth_url})")
else:
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # Huidig nummer ophalen
    current_track = sp.current_playback()

    if current_track and current_track['item']:
        track = current_track['item']
        track_name = track['name']
        artist = ", ".join([a['name'] for a in track['artists']])
        album_cover_url = track['album']['images'][0]['url']

        # Album cover laden
        response = requests.get(album_cover_url)
        album_cover = Image.open(BytesIO(response.content))

        # Glow-effect maken
        glow = album_cover.convert("RGB").resize((600, 600))
        glow = glow.filter(ImageFilter.GaussianBlur(40))

        # CSS voor CarPlay style
        st.markdown("""
            <style>
                body { background-color: black; }
                .carplay-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    margin-top: -50px;
                }
                .spotify-logo {
                    width: 120px;
                    margin-bottom: 20px;
                }
                .album-container {
                    position: relative;
                }
                .glow {
                    border-radius: 30px;
                    box-shadow: 0px 0px 60px 20px rgba(30,215,96,0.7);
                }
                .track-info {
                    font-size: 28px;
                    font-weight: bold;
                    color: white;
                    margin-top: 20px;
                }
                .artist-info {
                    font-size: 20px;
                    color: #b3b3b3;
                }
                .controls {
                    display: flex;
                    justify-content: center;
                    margin-top: 40px;
                    gap: 40px;
                }
                .control-btn {
                    background-color: #1DB954;
                    color: white;
                    font-size: 28px;
                    padding: 20px;
                    border-radius: 50%;
                    border: none;
                    cursor: pointer;
                    transition: 0.2s;
                }
                .control-btn:hover {
                    background-color: #1ed760;
                }
            </style>
        """, unsafe_allow_html=True)

        # Layout CarPlay
        st.markdown('<div class="carplay-container">', unsafe_allow_html=True)

        # Spotify logo
        spotify_logo = "https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg"
        st.markdown(f'<img src="{spotify_logo}" class="spotify-logo"/>', unsafe_allow_html=True)

        # Album cover + glow
        st.image(glow, use_container_width=False, caption="", output_format="PNG")
        st.image(album_cover, width=300, caption="", output_format="PNG")

        # Track info
        st.markdown(f'<div class="track-info">{track_name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="artist-info">{artist}</div>', unsafe_allow_html=True)

        # Controls
        st.markdown("""
            <div class="controls">
                <button class="control-btn">⏮</button>
                <button class="control-btn">▶️</button>
                <button class="control-btn">⏭</button>
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.write("Geen muziek speelt momenteel 🎵")



