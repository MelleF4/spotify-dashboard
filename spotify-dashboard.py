import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# ===============================
# Spotify API settings
# ===============================
CLIENT_ID = "cefb6e54f4914a8283255ee8b7ae3396"
CLIENT_SECRET = "df02aafe4e5240db82b5ab127b887212"
REDIRECT_URI = "https://example.org/callback"  # moet exact gelijk zijn aan Spotify Developer Dashboard

SCOPE = "user-read-playback-state user-read-currently-playing"

# ===============================
# Auth manager met cache
# ===============================
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".cache-spotify",   # sla tokens op
    show_dialog=True               # dwing login af
)

sp = spotipy.Spotify(auth_manager=sp_oauth)

# ===============================
# Streamlit UI
# ===============================
st.title("🚴‍♂️ Bike Spotify Dashboard")

# Debug: laat token info zien
token_info = sp_oauth.get_access_token(as_dict=True)
st.write("Token info:", token_info)

# ===============================
# Huidige track ophalen
# ===============================
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
