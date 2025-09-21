# spotify_dashboard_pro.py
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pandas as pd
import plotly.express as px

import requests
import tempfile
from colorthief import ColorThief
import math

# -------------------- Helpers --------------------
def rgb_to_hex(rgb_tuple):
    return '#%02x%02x%02x' % rgb_tuple

def get_dominant_color_from_url(url):
    """Download image to temp file and return dominant RGB hex via ColorThief.
       Returns None if fails."""
    try:
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=True, suffix=".jpg") as f:
            f.write(r.content)
            f.flush()
            ct = ColorThief(f.name)
            dominant = ct.get_color(quality=1)
            return rgb_to_hex(dominant)
    except Exception:
        return None

def sec_to_hms(sec):
    sec = int(round(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"

# -------------------- CSS base (we will inject dynamic bg later) --------------------
BASE_CSS = """
<style>
/* App layout */
body, .stApp { background-color: #0d0d0d; margin:0; padding:0; height:100vh; overflow:hidden; }
.app-wrap { height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; }

/* Spotify tile - we'll override background-color inline */
.spotify-tile {
    width: 96%;
    max-width: 820px;
    border-radius: 14px;
    padding: 14px;
    margin-top: 10px;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    box-sizing: border-box;
    transition: background 0.4s ease, transform 0.25s ease;
}
.spotify-tile:hover { transform: translateY(-3px); }

/* album & text */
.row { display:flex; align-items:center; gap:12px; }
.album-art { width:70px; height:auto; border-radius:8px; animation: pulse 1.5s infinite; box-shadow: 0 6px 18px rgba(0,0,0,0.6); }
@keyframes pulse { 0%{transform:scale(1);opacity:0.95} 50%{transform:scale(1.04);opacity:1} 100%{transform:scale(1);opacity:0.95} }

.track-info { text-align:left; overflow:hidden; }
.track-title { font-weight:700; font-size:16px; margin:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:520px; }
.track-artist { margin:0; font-size:12px; color:rgba(255,255,255,0.85); }

/* progress */
.progress-container { background: rgba(0,0,0,0.35); border-radius:6px; height:7px; width:100%; margin-top:8px; overflow:hidden; }
.progress-bar { height:100%; border-radius:6px; transition: width 0.5s linear; }

/* equalizer */
.equalizer { display:inline-flex; gap:4px; align-items:end; margin-left:6px; }
.eq-bar { width:4px; background: rgba(255,255,255,0.9); border-radius:2px; animation: eq 0.9s infinite linear; opacity:0.9; transform-origin: bottom; }
.eq-bar.eq-1 { animation-delay: 0s; }
.eq-bar.eq-2 { animation-delay: 0.12s; }
.eq-bar.eq-3 { animation-delay: 0.24s; }
@keyframes eq {
  0% { height:6px; opacity:0.6 }
  50% { height:20px; opacity:1 }
  100% { height:6px; opacity:0.6 }
}

/* control buttons row */
.controls { display:flex; justify-content:center; gap:28px; margin-top:10px; align-items:center; }
.stButton>button { width:46px; height:46px; border-radius:50%; background:#222; color:white; border:none; font-size:18px; transition: all 0.18s ease; }
.stButton>button:hover { transform:scale(1.12); background:#1DB954; color:black; box-shadow: 0 6px 18px rgba(29,185,84,0.18); }

/* small text */
.small { font-size:12px; color:rgba(255,255,255,0.85); }

/* Ritten tile and dashboard styles */
.rit-tile, .dash-tile {
    width: 96%;
    max-width: 820px;
    border-radius: 12px;
    padding: 10px;
    margin-top: 12px;
    background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
    box-sizing: border-box;
}

/* hide Streamlit default footer/padding that may cause scrollbars */
footer {visibility:hidden;}
header {visibility:hidden;}
</style>
"""

st.set_page_config(page_title="Spotify Ride Dashboard", layout="centered", initial_sidebar_state="expanded")
st.markdown(BASE_CSS, unsafe_allow_html=True)

# -------------------- Spotify Auth --------------------
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing,user-read-currently-playing"

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        redirect_uri=REDIRECT_URI,
                        scope=SCOPE,
                        cache_path=".cache-spotify",
                        show_dialog=True)

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

# -------------------- Auto-refresh --------------------
# Spotify info refresh often to animate equalizer & progress
st_autorefresh(interval=1500, key="spotify-refresh")

# -------------------- Sidebar Pages --------------------
page = st.sidebar.radio("Navigatie", ["Spotify", "Ritten", "Dashboard"])

# Ensure ride log in session
if "ride_log" not in st.session_state:
    st.session_state.ride_log = []
if "last_ride_id" not in st.session_state:
    st.session_state.last_ride_id = 0

# -------------------- Spotify Page --------------------
if page == "Spotify":
    # fetch playback info
    try:
        current = sp.current_playback()
    except Exception:
        current = None

    # default accent
    accent_hex = "#1DB954"

    album_url = None
    is_playing = False
    track = None
    artist_names = None
    progress_pct = 0

    if current and current.get("item"):
        is_playing = bool(current.get("is_playing"))
        item = current["item"]
        track = item.get("name")
        artists = item.get("artists", [])
        artist_names = ", ".join([a.get("name") for a in artists])
        album_images = item.get("album", {}).get("images", [])
        if album_images:
            album_url = album_images[0].get("url")
        try:
            progress_ms = current.get("progress_ms", 0)
            duration_ms = item.get("duration_ms", 1)
            progress_pct = int((progress_ms / max(duration_ms,1)) * 100)
        except Exception:
            progress_pct = 0

        # try to extract dominant color
        if album_url:
            color_hex = get_dominant_color_from_url(album_url)
            if color_hex:
                accent_hex = color_hex

    # build inline style for spotify tile using accent color (a bit darkened for bg)
    # create a translucent background using rgb
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    try:
        r,g,b = hex_to_rgb(accent_hex)
        bg_style = f"background: linear-gradient(180deg, rgba({r},{g},{b},0.08), rgba({r},{g},{b},0.03)); border: none;"
        prog_style = f"background: linear-gradient(90deg, {accent_hex}, #1ed760);"
    except Exception:
        bg_style = ""
        prog_style = f"background: linear-gradient(90deg, #1DB954, #1ed760);"

    # render Spotify tile
    st.markdown(f'<div class="spotify-tile" style="{bg_style}">', unsafe_allow_html=True)

    # big spotify logo in header
    spotify_logo = "https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_CMYK_Green.png"
    st.image(spotify_logo, width=140)

    # content row
    if track:
        st.markdown('<div class="row">', unsafe_allow_html=True)
        # album
        if album_url:
            # album image
            st.markdown(f'<img class="album-art" src="{album_url}" />', unsafe_allow_html=True)
        # info
        st.markdown('<div class="track-info">', unsafe_allow_html=True)
        st.markdown(f'<div class="track-title">{track}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="track-artist small">{artist_names}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # progressbar (with accent)
        st.markdown(f'<div class="progress-container"><div class="progress-bar" style="width:{progress_pct}%; {prog_style}"></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="small">Geen afspeelinformatie beschikbaar</div>', unsafe_allow_html=True)

    # equalizer indicator (only visible when playing)
    if is_playing:
        st.markdown('<div style="margin-top:8px;"><span class="small">Now playing</span> <span class="equalizer"><div class="eq-bar eq-1" style="background:'+accent_hex+'"></div><div class="eq-bar eq-2" style="background:'+accent_hex+'"></div><div class="eq-bar eq-3" style="background:'+accent_hex+'"></div></span></div>', unsafe_allow_html=True)

    # controls centered with spacing
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("⏮", key="prev"):
            try: sp.previous_track()
            except: st.warning("Fout bij vorige track")
    with c2:
        if st.button("⏯", key="playpause"):
            try:
                current_state = sp.current_playback()
                if current_state and current_state.get("is_playing"):
                    sp.pause_playback()
                else:
                    sp.start_playback()
            except: st.warning("Fout bij play/pause")
    with c3:
        if st.button("⏭", key="next"):
            try: sp.next_track()
            except: st.warning("Fout bij volgende track")

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Ritten Page --------------------
elif page == "Ritten":
    st.markdown('<div class="rit-tile">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex;justify-content:space-between;align-items:center;">', unsafe_allow_html=True)
    st.markdown('<h4 style="margin:0;">🏁 Rit Tracker</h4>', unsafe_allow_html=True)

    col_start, col_stop = st.columns([1,1])
    with col_start:
        if st.button("▶️ Start Rit", key="start"):
            st.session_state.ride_start = datetime.now()
            st.session_state.last_ride_id += 1
    with col_stop:
        if st.button("⏹ Stop Rit", key="stop"):
            if "ride_start" in st.session_state:
                end = datetime.now()
                dur = (end - st.session_state.ride_start).total_seconds()
                st.session_state.ride_log.append({
                    "rit": st.session_state.last_ride_id,
                    "start": st.session_state.ride_start.strftime('%Y-%m-%d %H:%M:%S'),
                    "end": end.strftime('%Y-%m-%d %H:%M:%S'),
                    "sec": round(dur,1)
                })
                del st.session_state.ride_start

    if "ride_start" in st.session_state:
        live = (datetime.now() - st.session_state.ride_start).total_seconds()
        st.markdown(f'<div class="small">⏱️ Huidige rit: {round(live,1)} sec</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="progress-container"><div class="progress-bar" style="width:{min(live*2,100)}%; background:linear-gradient(90deg, #1DB954, #1ed760);"></div></div>', unsafe_allow_html=True)

    df = pd.DataFrame(st.session_state.ride_log)
    st.dataframe(df[['rit','start','end','sec']] if not df.empty else df, height=220)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", csv, "ride_log.csv")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Dashboard Page --------------------
elif page == "Dashboard":
    st.markdown('<div class="dash-tile">', unsafe_allow_html=True)
    st.subheader("📊 Rit Statistieken")
    df = pd.DataFrame(st.session_state.ride_log)
    if not df.empty:
        total = len(df)
        avg_sec = df['sec'].mean()
        longest = df['sec'].max()
        shortest = df['sec'].min()
        total_time = df['sec'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Totaal ritten", total)
        col2.metric("Gem. duur", sec_to_hms(avg_sec))
        col3.metric("Langste rit", sec_to_hms(longest))
        col4.metric("Totale tijd", sec_to_hms(total_time))

        # grafiek
        fig = px.bar(df, x='rit', y='sec', labels={'sec':'Duur (s)', 'rit':'Rit #'}, color='sec', color_continuous_scale=['#1DB954','#1ed760'])
        fig.update_layout(plot_bgcolor='#0d0d0d', paper_bgcolor='#0d0d0d', font_color='white', height=300, margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nog geen ritten. Start een rit om statistieken te verzamelen.")
    st.markdown('</div>', unsafe_allow_html=True)
