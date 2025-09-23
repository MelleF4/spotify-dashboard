import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import folium
from streamlit_folium import st_folium
from PIL import Image
from io import BytesIO

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
# Spotify login handmatig
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

    st.set_page_config(page_title="CarPlay Dashboard", layout="wide")
    st.markdown(
        """
        <style>
        body {
            background-color: #0d0d0d;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .tile {
            background-color: #121212;
            border-radius: 25px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.5);
        }
        .spotify-logo {
            width: 120px;
            margin-bottom: 10px;
        }
        .track-info {
            font-size: 20px;
            font-weight: 600;
        }
        .artist-info {
            font-size: 14px;
            color: #b3b3b3;
        }
        .controls button {
            background-color: #1DB954;
            border: none;
            color: white;
            padding: 12px 20px;
            margin: 0 10px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s ease-in-out;
        }
        .controls button:hover {
            transform: scale(1.2);
            box-shadow: 0 0 10px #1DB954;
        }
        .cover-glow {
            border-radius: 15px;
            box-shadow: 0 0 30px rgba(29,185,84,0.7);
        }
        .map-tile {
            background-color: #121212;
            border-radius: 25px;
            padding: 15px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.5);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # =========================
    # Spotify tile
    # =========================
    with st.container():
        st.markdown('<div class="tile" style="text-align:center;">', unsafe_allow_html=True)
        st.image("https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_White.png", width=120)

        current = sp.current_playback()
        if current and current.get("item"):
            track = current["item"]["name"]
            artist = ", ".join([a["name"] for a in current["item"]["artists"]])
            cover = current["item"]["album"]["images"][1]["url"]

            response = requests.get(cover)
            img = Image.open(BytesIO(response.content))
            st.image(img, width=140, use_column_width=False, clamp=True, output_format="PNG", caption=None)

            st.markdown(f"<div class='track-info'>{track}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='artist-info'>{artist}</div>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1,1,1])
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
    st.markdown('<div class="map-tile">', unsafe_allow_html=True)
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
        m = folium.Map(location=start_coords, zoom_start=9, tiles="CartoDB dark_matter")
        folium.Marker(start_coords, tooltip="Start").add_to(m)
        folium.Marker(end_coords, tooltip="Eind").add_to(m)
        folium.PolyLine([[lat, lon] for lon, lat in coords], color="#1DB954", weight=5).add_to(m)
        st_folium(m, width=700, height=400)
    else:
        st.warning("Kon geen route ophalen. Controleer ORS_API_KEY of netwerk.")

    st.markdown('</div>', unsafe_allow_html=True)

