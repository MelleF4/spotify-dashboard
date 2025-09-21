import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from streamlit_autorefresh import st_autorefresh

# ===============================
# Spotify API settings via secrets
# ===============================
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

SCOPE = "user-read-playback-state user-read-currently-playing"

# ===============================
# Auth manager met cache
# ===============================
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".cache-spotify",
    show_dialog=True
)

# ===============================
# Check of er al een token in cache staat
# ===============================
token_info = sp_oauth.get_cached_token()
if not token_info:
    st.info("🎯 Eerst even inloggen bij Spotify")
    auth_url = sp_oauth.get_authorize_url()
    st.write(f"[Klik hier om in te loggen]({auth_url})")
    code = st.text_input("Plak hier de URL waar je naartoe werd gestuurd:", "")
    if code:
        code = sp_oauth.parse_response_code(code)
        token_info = sp_oauth.get_access_token(code)
        st.success("✅ Inloggen gelukt!")

# ===============================
# Spotipy client
# ===============================
sp = spotipy.Spotify(auth_manager=sp_oauth)

# ===============================
# Auto-refresh elke 5 seconden
# ===============================
st_autorefresh(interval=5000, key="spotify-refresh")  # refresh elke 5 seconden

# ===============================
# Streamlit UI
# ===============================
st.title("🚴‍♂️ Bike Spotify Dashboard")

try:
    current = sp.current_playback()
    if current and current.get("is_playing"):
        track = current["item"]["name"]
        artist = ", ".join([a["name"] for a in current["item"]["artists"]])
        st.subheader(f"▶️ Now Playing: {track} - {artist}")
        st.image(current["item"]["album"]["images"][0]["url"])
    else:
        st.subheader("⏸️ Niks speelt nu")
except Exception as e:
    st.error(f"Fout bij ophalen: {e}")
