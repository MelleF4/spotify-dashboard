import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pandas as pd

# ---------- CSS voor ultra-compact tiles ----------
st.markdown(
    """
    <style>
    .main {
        padding: 0px 3px;
    }

    .tile {
        border: 2px solid #1DB954;
        border-radius: 8px;
        padding: 4px;          /* super compact */
        margin-bottom: 6px;
        background-color: #121212;
        color: white;
        font-size: 0.8rem;     /* kleiner lettertype */
    }

    .tile img {
        max-width: 80px;       /* kleinere album-art */
        height: auto;
    }

    .stDataFrame div[data-testid="stVerticalBlock"] {
        max-height: 150px;
        overflow-y: auto;
    }

    /* Compact buttons */
    .stButton>button {
        padding: 4px 6px;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Meta tags voor fullscreen ----------
st.markdown(
    """
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    </head>
    """,
    unsafe_allow_html=True
)

# ---------- Spotify Auth ----------
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".cache-spotify",
    show_dialog=True
)

token_info = sp_oauth.get_cached_token()
if not token_info:
    st.info("🎯 Eerst inloggen bij Spotify")
    auth_url = sp_oauth.get_authorize_url()
    st.write(f"[Klik hier om in te loggen]({auth_url})")
    code = st.text_input("Plak hier de URL waar je naartoe werd gestuurd:", "")
    if code:
        code = sp_oauth.parse_response_code(code)
        token_info = sp_oauth.get_access_token(code)
        st.success("✅ Inloggen gelukt!")

sp = spotipy.Spotify(auth_manager=sp_oauth)

# ---------- Auto-refresh ----------
st_autorefresh(interval=5000, key="spotify-refresh")

# ---------- 2 Tiles: Spotify | Rit ----------
tile_spotify, tile_rit = st.columns([1.2,1])

# -------- Spotify tile --------
with tile_spotify:
    st.markdown('<div class="tile">', unsafe_allow_html=True)
    st.subheader("🎵 Spotify")

    try:
        current = sp.current_playback()
        if current and current.get("is_playing"):
            track = current["item"]["name"]
            artist_names = ", ".join([a["name"] for a in current["item"]["artists"]])
            st.image(current["item"]["album"]["images"][0]["url"])
            st.write(f"**{track}** - {artist_names}")

            duration_ms = current["item"]["duration_ms"]
            progress_ms = current["progress_ms"]
            new_pos = st.slider("", 0, duration_ms, progress_ms)
            if st.button("⏩"):  # kleinere button
                sp.seek_track(new_pos)
        else:
            st.write("⏸️ Niks speelt nu")
    except Exception as e:
        st.error(f"Fout bij ophalen: {e}")

    # Playback controls (emoji-only)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⏮"):
            sp.previous_track()
    with c2:
        if st.button("⏯"):
            current = sp.current_playback()
            if current and current["is_playing"]:
                sp.pause_playback()
            else:
                sp.start_playback()
    with c3:
        if st.button("⏭"):
            sp.next_track()
    st.markdown('</div>', unsafe_allow_html=True)

# -------- Rit tile --------
with tile_rit:
    st.markdown('<div class="tile">', unsafe_allow_html=True)
    st.subheader("🏁 Rit Tracker")

    if "ride_log" not in st.session_state:
        st.session_state.ride_log = []
    if "last_ride_id" not in st.session_state:
        st.session_state.last_ride_id = 0

    if st.button("▶️"):
        st.session_state.ride_start = datetime.now()
        st.session_state.last_ride_id += 1
        st.success(f"Rit #{st.session_state.last_ride_id} gestart!")

    if st.button("⏹"):
        if "ride_start" in st.session_state:
            end_time = datetime.now()
            st.session_state.ride_log.append({
                "rit_id": st.session_state.last_ride_id,
                "start": st.session_state.ride_start.strftime('%Y-%m-%d %H:%M:%S'),
                "end": end_time.strftime('%Y-%m-%d %H:%M:%S')
            })
            st.success(f"Rit #{st.session_state.last_ride_id} gestopt!")
            del st.session_state.ride_start
        else:
            st.warning("Start eerst een rit!")

    df_log = pd.DataFrame(st.session_state.ride_log)
    st.dataframe(df_log, height=150)

    csv = df_log.to_csv(index=False).encode("utf-8")
    st.download_button("📥 CSV", csv, "ride_log.csv", key="download")
    st.markdown('</div>', unsafe_allow_html=True)

