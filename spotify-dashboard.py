import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pandas as pd

# ---------- CSS ultra-ultra-compact ----------
st.markdown(
    """
    <style>
    .main {padding: 0px 1px;}
    .tile {
        border: 1px solid #1DB954;
        border-radius: 5px;
        padding: 1px;
        margin-bottom: 2px;
        background-color: #121212;
        color: white;
        font-size: 0.6rem;
    }
    .tile img {max-width: 30px; height:auto;}
    .stDataFrame div[data-testid="stVerticalBlock"] {
        max-height: 100px; overflow-y:auto;
        font-size:0.6rem;
    }
    .stButton>button {padding:1px 2px; font-size:0.6rem;}
    .spotify-playing {animation: pulse 1s infinite;}
    @keyframes pulse {0%{opacity:0.6;}50%{opacity:1;}100%{opacity:0.6;}}
    </style>
    """, unsafe_allow_html=True
)

# ---------- Meta tags fullscreen ----------
st.markdown(
    """
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True
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
st_autorefresh(interval=2000, key="spotify-refresh")

# ---------- Columns ----------
tile_spotify, tile_rit = st.columns([1.2,1])

# -------- Spotify tile --------
with tile_spotify:
    st.markdown('<div class="tile">', unsafe_allow_html=True)
    st.subheader("🎵 Spotify")
    try:
        current = sp.current_playback()
        if current:
            track = current["item"]["name"]
            artist_names = ", ".join([a["name"] for a in current["item"]["artists"]])
            st.image(current["item"]["album"]["images"][0]["url"])
            status = "▶️" if current["is_playing"] else "⏸"
            st.markdown(f'<span class="spotify-playing">{status}</span> {track} - {artist_names}', unsafe_allow_html=True)
        else:
            st.write("⏸️ Niks speelt nu")
    except:
        st.write("Fout bij ophalen Spotify")
    # Playback controls
    c1,c2,c3 = st.columns(3)
    with c1: st.button("⏮", key="prev")
    with c2: st.button("⏯", key="playpause")
    with c3: st.button("⏭", key="next")
    st.markdown('</div>', unsafe_allow_html=True)

# -------- Rit tile --------
with tile_rit:
    st.markdown('<div class="tile">', unsafe_allow_html=True)
    st.subheader("🏁 Rit Tracker")
    if "ride_log" not in st.session_state: st.session_state.ride_log=[]
    if "last_ride_id" not in st.session_state: st.session_state.last_ride_id=0

    if st.button("▶️", key="start"):
        st.session_state.ride_start=datetime.now()
        st.session_state.last_ride_id+=1
    if st.button("⏹", key="stop"):
        if "ride_start" in st.session_state:
            end=datetime.now()
            dur=(end-st.session_state.ride_start).total_seconds()
            st.session_state.ride_log.append({
                "rit":st.session_state.last_ride_id,
                "start":st.session_state.ride_start.strftime('%H:%M:%S'),
                "end":end.strftime('%H:%M:%S'),
                "sec":round(dur,1)
            })
            del st.session_state.ride_start

    # Live ritduur
    if "ride_start" in st.session_state:
        live=(datetime.now()-st.session_state.ride_start).total_seconds()
        st.write(f"⏱️ Huidige rit: {round(live,1)} sec")

    df=pd.DataFrame(st.session_state.ride_log)
    st.dataframe(df, height=100)
    csv=df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 CSV", csv, "ride_log.csv", key="dl")
    st.markdown('</div>', unsafe_allow_html=True)
