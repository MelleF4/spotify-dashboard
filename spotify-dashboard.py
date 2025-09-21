import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pandas as pd
import plotly.express as px

# -------------------- CSS Styling --------------------
st.markdown("""
<style>
body, .stApp {
    background-color: #121212;
    font-family: Arial, sans-serif;
    color: white;
    margin: 0;
    padding: 0;
    overflow: hidden; /* geen scrollen */
    height: 100vh;
}
.tile {
    padding: 10px;
    margin-bottom: 10px;
    background: transparent; /* geen randen/schaduw */
    color: white;
    font-size: 0.8rem;
    text-align: center;
    animation: fadeIn 0.8s ease;
}
.stButton>button {
    padding: 14px;
    font-size: 1.2rem;
    border-radius: 50%;
    transition: all 0.2s ease;
    background-color: #222;
    color: white;
    border: none;
    margin: 0 20px;
}
.stButton>button:hover {
    background-color: #1DB954;
    color: black;
    transform: scale(1.15);
    box-shadow: 0 4px 12px rgba(29,185,84,0.6);
}
.album-art {
    max-width: 70px;
    border-radius: 10px;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% {transform: scale(1); opacity: 0.9;}
    50% {transform: scale(1.05); opacity: 1;}
    100% {transform: scale(1); opacity: 0.9;}
}
.progress-container {
    background-color: #333;
    width: 100%;
    border-radius: 4px;
    height: 6px;
    margin: 8px 0;
}
.progress-bar {
    background: linear-gradient(90deg, #1DB954, #1ed760);
    height: 6px;
    border-radius: 4px;
    transition: width 0.5s ease;
}
@keyframes fadeIn {
    from {opacity:0; transform:translateY(10px);}
    to {opacity:1; transform:translateY(0);}
}
.now-playing {
    width: 100%;
    overflow: hidden;
    white-space: nowrap;
    box-sizing: border-box;
}
.now-playing span {
    display: inline-block;
    padding-left: 100%;
    animation: scroll-text 12s linear infinite;
}
@keyframes scroll-text {
    0% {transform: translateX(0);}
    100% {transform: translateX(-100%);}
}
</style>
""", unsafe_allow_html=True)

# -------------------- Spotify Auth --------------------
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

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
st_autorefresh(interval=2500, key="spotify-refresh")

# -------------------- Sidebar Pages --------------------
page = st.sidebar.radio("📂 Navigatie", ["Spotify", "Rit Tracker", "Dashboard"])

# -------------------- Spotify Page --------------------
if page == "Spotify":
    try:
        current = sp.current_playback()
        if current and current["item"]:
            track = current["item"]["name"]
            artist_names = ", ".join([a["name"] for a in current["item"]["artists"]])

            # Spotify-logo als eye-catcher
            spotify_logo = "https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_CMYK_Green.png"
            st.image(spotify_logo, width=200)

            # Album art
            st.image(current["item"]["album"]["images"][0]["url"], width=70)

            # Track + artiest als scrollende tekst
            st.markdown(f"""
            <div class="now-playing"><span>🎶 {track} — {artist_names}</span></div>
            """, unsafe_allow_html=True)

            # Progressbar
            progress_ms = current["progress_ms"]
            duration_ms = current["item"]["duration_ms"]
            progress_pct = int((progress_ms/duration_ms)*100)
            st.markdown(f'<div class="progress-container"><div class="progress-bar" style="width:{progress_pct}%"></div></div>', unsafe_allow_html=True)
        else:
            st.write("⏸️ Niks speelt nu")
    except:
        st.write("⚠️ Fout bij ophalen Spotify")

    # Media knoppen gecentreerd
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("⏮", key="prev"): 
            try: sp.previous_track()
            except: st.warning("Fout bij vorige track")
    with c2:
        if st.button("⏯", key="playpause"): 
            try:
                current = sp.current_playback()
                if current and current["is_playing"]:
                    sp.pause_playback()
                else:
                    sp.start_playback()
            except: st.warning("Fout bij play/pause")
    with c3:
        if st.button("⏭", key="next"): 
            try: sp.next_track()
            except: st.warning("Fout bij volgende track")

# -------------------- Rit Tracker Page --------------------
elif page == "Rit Tracker":
    st.subheader("🏁 Rit Tracker")
    if "ride_log" not in st.session_state: st.session_state.ride_log=[]
    if "last_ride_id" not in st.session_state: st.session_state.last_ride_id=0

    if st.button("▶️ Start Rit", key="start"):
        st.session_state.ride_start=datetime.now()
        st.session_state.last_ride_id+=1
    if st.button("⏹ Stop Rit", key="stop"):
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

    if "ride_start" in st.session_state:
        live=(datetime.now()-st.session_state.ride_start).total_seconds()
        st.write(f"⏱️ Huidige rit: {round(live,1)} sec")
        st.markdown(f'<div class="progress-container"><div class="progress-bar" style="width:{min(live*2,100)}%"></div></div>', unsafe_allow_html=True)

    df=pd.DataFrame(st.session_state.ride_log)
    st.dataframe(df, height=160)
    csv=df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 CSV", csv, "ride_log.csv", key="dl")

# -------------------- Dashboard Page --------------------
elif page == "Dashboard":
    st.subheader("📊 Rit Dashboard")
    if "ride_log" in st.session_state and st.session_state.ride_log:
        df=pd.DataFrame(st.session_state.ride_log)
        fig = px.bar(df, x="rit", y="sec",
                     labels={"sec":"Duur (s)","rit":"Ritnummer"},
                     title="⏱ Ritduur per rit",
                     color="sec",
                     color_continuous_scale=["#1DB954", "#1ed760"])
        fig.update_layout(
            height=300,
            margin=dict(l=10,r=10,t=40,b=10),
            font=dict(size=12,color="white"),
            plot_bgcolor="#121212",
            paper_bgcolor="#121212"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("🚴 Geen ritdata beschikbaar")


