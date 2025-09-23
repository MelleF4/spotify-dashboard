import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import folium
from streamlit_folium import st_folium

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
# Spotify login (handmatig)
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

    # CarPlay-style tile
    st.set_page_config(page_title="CarPlay Dashboard", layout="wide")
    st.markdown(
        """
        <style>
        .spotify-tile {
            background-color: #121212;
            border-radius: 20px;
            padding: 15px;
            text-align: center;
            color: white;
            margin-bottom: 20px;
        }
        .spotify-logo {
            width: 100px;
            margin-bottom: 10px;
        }
        .track-info {
            font-size: 18px;
            font-weight: bold;
        }
        .artist-info {
            font-size: 14px;
            color: #b3b3b3;
        }
        .controls button {
            background-color: #1DB954;
            border: none;
            color: white;
            padding: 10px 16px;
            margin: 0 5px;
            border-radius: 30px;
            cursor: pointer;
            font-size: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.container():
        st.markdown('<div class="spotify-tile">', unsafe_allow_html=True)
        st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_White.png", width=120)

        current = sp.current_playback()
        if current and current.get("item"):
            track = current["item"]["name"]
            artist = ", ".join([a["name"] for a in current["item"]["artists"]])
            cover = current["item"]["album"]["images"][1]["url"]

            st.image(cover, width=150)
            st.markdown(f"<div class='track-info'>{track}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='artist-info'>{artist}</div>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("⏮️"):
                    sp.previous_track()
            with col2:
                if st.button("⏯️"):
                    if current["is_playing"]:
                        sp.pause_playback()
                    else:
                        sp.start_playback()
            with col3:
                if st.button("⏭️"):
                    sp.next_track()
        else:
            st.write("Geen muziek aan het spelen.")

        st.markdown('</div>', unsafe_allow_html=True)

    # =========================
    # Navigatie kaart
    # =========================
    st.markdown("### Navigatie")

    start_coords = [52.3676, 4.9041]  # Amsterdam
    end_coords = [52.0907, 5.1214]    # Utrecht

    BASE_URL = "https://api.openrouteservice.org/v2/directions/driving-car"
    ORS_API_KEY = st.secrets.get("ORS_API_KEY", "demo")

    def get_route(start, end):
        headers = {"Authorization": ORS_API_KEY}
        params = {"start": f"{start[1]},{start[0]}", "end": f"{end[1]},{end[0]}"}
        r = requests.get(BASE_URL, headers=headers, params=params)
        if r.status_code != 200:
            return None
        return r.json()

    route_data = get_route(start_coords, end_coords)
    if route_data:
        coords = route_data["features"][0]["geometry"]["coordinates"]
        m = folium.Map(location=start_coords, zoom_start=9)
        folium.Marker(start_coords, tooltip="Start").add_to(m)
        folium.Marker(end_coords, tooltip="Eind").add_to(m)
        folium.PolyLine([[lat, lon] for lon, lat in coords], color="blue").add_to(m)
        st_folium(m, width=700, height=400)
    else:
        st.warning("Kon geen route ophalen. Controleer ORS_API_KEY of netwerk.")


