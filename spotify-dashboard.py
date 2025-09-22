# spotify_dashboard.py
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from io import BytesIO
from PIL import Image
from colorthief import ColorThief
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import time
import plotly.express as px

# -------------------------
# CONFIG / SECRETS
# -------------------------
st.set_page_config(page_title="Spotify Ride Dashboard", page_icon="🎵", layout="wide")
# Make sure you have CLIENT_ID, CLIENT_SECRET, REDIRECT_URI in Streamlit secrets.
CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

# -------------------------
# Spotify auth
# -------------------------
# Use cache_path so the refresh token is stored in a local file (.cache-spotify)
auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".cache-spotify",
    show_dialog=True
)
sp = spotipy.Spotify(auth_manager=auth_manager)

# -------------------------
# Helpers: color, track, geocode, routing
# -------------------------
def rgb_to_css(r,g,b,a=1.0):
    return f"rgba({r},{g},{b},{a})"

def get_current_track_info():
    """Return dict with track info or None."""
    try:
        current = sp.current_playback()
    except Exception:
        return None
    if not current or not current.get("item"):
        return None
    item = current["item"]
    title = item.get("name", "")
    artists = ", ".join([a.get("name","") for a in item.get("artists",[])])
    images = item.get("album", {}).get("images", [])
    cover = images[0]["url"] if images else None
    is_playing = bool(current.get("is_playing"))
    progress_ms = current.get("progress_ms", 0)
    duration_ms = item.get("duration_ms", 1)
    try:
        # try dominant color
        resp = requests.get(cover, timeout=4)
        resp.raise_for_status()
        ct = ColorThief(BytesIO(resp.content))
        dominant = ct.get_color(quality=1)
    except Exception:
        dominant = (30,215,96)  # spotify green fallback
    return {
        "title": title,
        "artists": artists,
        "cover": cover,
        "is_playing": is_playing,
        "progress_pct": int((progress_ms / max(duration_ms,1)) * 100),
        "dominant": dominant
    }

# Geocoding with Nominatim (OpenStreetMap) - cached for repeated queries
@st.cache_data(ttl=60*60)
def geocode_address(q):
    """Return (lat, lon) for address q or None."""
    q = q.strip()
    # If already lat,lon string -> parse
    if "," in q:
        try:
            parts = [p.strip() for p in q.split(",")]
            if len(parts) == 2:
                lat = float(parts[0]); lon = float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
        except Exception:
            pass
    NOMINATIM = "https://nominatim.openstreetmap.org/search"
    try:
        res = requests.get(NOMINATIM, params={"q": q, "format": "json", "limit": 1},
                           headers={"User-Agent":"SpotifyRideDashboard/1.0 (+https://example.org)"},
                           timeout=8)
        res.raise_for_status()
        data = res.json()
        if not data:
            return None
        lat = float(data[0]["lat"]); lon = float(data[0]["lon"])
        return lat, lon
    except Exception:
        return None

@st.cache_data(ttl=60*10)
def osrm_route(lat1, lon1, lat2, lon2):
    """
    Query public OSRM instance for route.
    Returns dict with geojson, steps, distance_m, duration_s or None on failure.
    """
    OSRM = "http://router.project-osrm.org/route/v1/driving"
    coords = f"{lon1},{lat1};{lon2},{lat2}"
    params = {"overview":"full", "geometries":"geojson", "steps":"true", "annotations":"duration,distance"}
    try:
        r = requests.get(f"{OSRM}/{coords}", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != "Ok":
            return None
        route = data["routes"][0]
        geojson = route["geometry"]  # LineString
        distance_m = route.get("distance", 0)
        duration_s = route.get("duration", 0)
        steps = []
        for leg in route.get("legs", []):
            for s in leg.get("steps", []):
                maneuver = s.get("maneuver", {})
                typ = maneuver.get("type", "")
                mod = maneuver.get("modifier", "")
                name = s.get("name","")
                # build user-friendly instruction
                txt = ""
                if typ:
                    txt = typ
                if mod:
                    txt += f" {mod}"
                if name:
                    txt += f" onto {name}"
                txt = txt.strip()
                steps.append({"text": txt if txt else name, "distance_m": s.get("distance",0)})
        return {"geojson": geojson, "steps": steps, "distance_m": distance_m, "duration_s": duration_s}
    except Exception:
        return None

# -------------------------
# UI Styling (CarPlay-like dark)
# -------------------------
st.markdown("""
<style>
/* remove default padding */
.block-container { padding: 0 6px; }

/* overall background */
html, body, .stApp {
  background: linear-gradient(180deg,#070707,#0a0a0a);
}

/* header logo center */
.top-logo { display:flex; justify-content:center; padding-top:10px; }

/* spotify tile */
.spotify-tile { text-align:center; padding:12px 8px; margin-top:6px; }

/* album glow is set inline via box-shadow in the img tag */

/* visualizer */
.viz { display:flex; justify-content:center; gap:6px; margin-top:8px; }
.viz .bar { width:6px; background:white; border-radius:3px; animation:bounce 1s infinite; opacity:0.95; }
.viz .bar.b2 { animation-delay:0.12s; }
.viz .bar.b3 { animation-delay:0.24s; }
@keyframes bounce { 0%,100%{height:12px;} 50%{height:34px;} }

/* control buttons style */
.controls { display:flex; justify-content:center; gap:28px; margin-top:12px; }
.controls button { width:64px; height:64px; border-radius:50%; border:none; background:#111; color:white; font-size:20px; transition:transform .12s ease; }
.controls button:hover { transform:scale(1.08); background:#1DB954; color:#000; box-shadow:0 8px 24px rgba(29,185,84,0.18); }

/* tabs content */
.tab-block { padding:12px 8px; }

/* small muted */
.muted { color: rgba(255,255,255,0.75); font-size:13px; }

/* metrics */
.metric-box { display:flex; gap:14px; justify-content:space-around; align-items:center; margin-top:8px; }
.metric { background: rgba(255,255,255,0.03); padding:10px 14px; border-radius:10px; width:22%; text-align:center; }

/* make folium map center nicely */
.folium-container { display:flex; justify-content:center; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Session state init for rides
# -------------------------
if "rides" not in st.session_state:
    st.session_state["rides"] = []  # each ride: dict with start_ts, end_ts, sec, optional distance
if "ride_active" not in st.session_state:
    st.session_state["ride_active"] = False
if "ride_start_ts" not in st.session_state:
    st.session_state["ride_start_ts"] = None
if "refresh_interval" not in st.session_state:
    st.session_state["refresh_interval"] = 5  # seconds default

# -------------------------
# Page: top Spotify tile (always visible)
# -------------------------
track_info = None
try:
    track_info = get_current_track_info()
except Exception:
    track_info = None

st.markdown('<div class="top-logo"><img src="https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg" style="width:140px;"/></div>', unsafe_allow_html=True)
st.markdown('<div class="spotify-tile">', unsafe_allow_html=True)

if track_info:
    title = track_info["title"]
    artists = track_info["artists"]
    cover = track_info["cover"]
    dom = track_info["dominant"]
    is_playing = track_info["is_playing"]
    progress_pct = track_info["progress_pct"]
    r,g,b = dom

    # album with glow using dominant color
    box_css = f"box-shadow: 0 0 46px rgba({r},{g},{b},0.65);"
    st.markdown(f'''
        <div style="text-align:center;color:white;">
            <img src="{cover}" style="width:140px;border-radius:14px; {box_css}"/>
            <div style="font-weight:700; font-size:18px; margin-top:8px;">{title}</div>
            <div class="muted" style="margin-top:4px;">{artists}</div>
        </div>
    ''', unsafe_allow_html=True)

    # progress bar
    st.markdown(f'''
        <div style="width:80%; margin:10px auto 0; background:rgba(255,255,255,0.06); height:8px; border-radius:6px;">
            <div style="height:100%; width:{progress_pct}%; background: linear-gradient(90deg,#1DB954,#1ed760); border-radius:6px;"></div>
        </div>
    ''', unsafe_allow_html=True)

    # visualizer (only when playing)
    if is_playing:
        st.markdown('''
            <div class="viz">
                <div class="bar b1"></div>
                <div class="bar b2"></div>
                <div class="bar b3"></div>
            </div>
        ''', unsafe_allow_html=True)
    else:
        # small paused indicator
        st.markdown('<div class="muted" style="margin-top:8px;">⏸️ Paused</div>', unsafe_allow_html=True)

    # controls (use JS-free simple buttons)
    cols = st.columns([1,1,1])
    with cols[0]:
        if st.button("⏮️", key="prev_track"):
            try:
                sp.previous_track()
            except Exception:
                st.warning("Kon vorige track niet sturen.")
    with cols[1]:
        if st.button("⏯️", key="play_pause"):
            try:
                curr = sp.current_playback()
                if curr and curr.get("is_playing"):
                    sp.pause_playback()
                else:
                    sp.start_playback()
            except Exception:
                st.warning("Kon play/pause niet sturen.")
    with cols[2]:
        if st.button("⏭️", key="next_track"):
            try:
                sp.next_track()
            except Exception:
                st.warning("Kon volgende track niet sturen.")
else:
    st.markdown('<div style="text-align:center;color:white;padding:18px 0;">Geen afspeelinformatie beschikbaar</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Auto-refresh control in settings will adjust st.experimental_rerun interval; we do lightweight rerun on demand
# -------------------------
# Main tabs
# -------------------------
tabs = st.tabs(["🎵 Spotify", "🚴 Ritten", "📊 Statistieken", "⚙️ Instellingen", "🗺️ Navigatie"])

# --------- Tab 0: Spotify (more detailed controls / refresh) ----------
with tabs[0]:
    st.markdown('<div class="tab-block">', unsafe_allow_html=True)
    st.subheader("Spotify — controls & info")
    try:
        current = sp.current_playback()
    except Exception:
        current = None
    if current and current.get("item"):
        st.write(f"**{current['item']['name']}** — {', '.join([a['name'] for a in current['item']['artists']])}")
        st.write(f"Device: {current.get('device',{}).get('name','-')}")
        st.write(f"Context: {current.get('context', {}).get('type','-')}")
    else:
        st.info("Geen muziek aan het spelen of geen device actief.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Tab 1: Ritten (start/stop, live) ----------
with tabs[1]:
    st.markdown('<div class="tab-block">', unsafe_allow_html=True)
    st.header("🚴 Rit Tracker")
    # start/stop
    if not st.session_state["ride_active"]:
        if st.button("▶️ Start rit"):
            st.session_state["ride_active"] = True
            st.session_state["ride_start_ts"] = time.time()
            st.success("Rit gestart")
    else:
        # show live time
        elapsed = time.time() - st.session_state["ride_start_ts"]
        st.markdown(f"⏱️ Huidige rit: **{int(elapsed)} sec**")
        if st.button("⏹ Stop rit"):
            duration = time.time() - st.session_state["ride_start_ts"]
            st.session_state["rides"].append({
                "start": datetime.fromtimestamp(st.session_state["ride_start_ts"]).strftime("%Y-%m-%d %H:%M:%S"),
                "end": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sec": round(duration,1)
            })
            st.session_state["ride_active"] = False
            st.session_state["ride_start_ts"] = None
            st.success("Rit opgeslagen")

    # show log
    if st.session_state["rides"]:
        df = pd.DataFrame(st.session_state["rides"])
        st.dataframe(df, use_container_width=True, height=240)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "ride_log.csv")
    else:
        st.info("Nog geen ritten gelogd.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Tab 2: Statistieken ----------
with tabs[2]:
    st.markdown('<div class="tab-block">', unsafe_allow_html=True)
    st.header("📊 Rit Statistieken")
    df = pd.DataFrame(st.session_state["rides"])
    if not df.empty:
        total = len(df)
        avg_sec = df["sec"].mean()
        longest = df["sec"].max()
        total_time = df["sec"].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Totaal ritten", total)
        c2.metric("Gem. duur", f"{round(avg_sec,1)} s")
        c3.metric("Langste rit", f"{round(longest,1)} s")
        c4.metric("Totale tijd", f"{round(total_time,1)} s")

        # plot durations
        fig = px.bar(df.reset_index().rename(columns={"index":"rit"}), x="rit", y="sec",
                     labels={"sec":"Duur (s)", "rit":"Rit #"}, color="sec",
                     color_continuous_scale=["#1DB954","#1ed760"])
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", height=320)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nog geen ritten om statistieken van te maken.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Tab 3: Instellingen ----------
with tabs[3]:
    st.markdown('<div class="tab-block">', unsafe_allow_html=True)
    st.header("⚙️ Instellingen")
    refresh = st.slider("Auto-refresh interval (sec) — affecteert hoe vaak je handmatig refrehs wilt doen", 3, 30, st.session_state["refresh_interval"])
    st.session_state["refresh_interval"] = refresh
    st.write("Huidige interval:", refresh, "s")
    st.markdown("**Tip:** Streamlit draait in de browser — je kunt `st.experimental_rerun()` handmatig uitvoeren wanneer je snel update wil forceren.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Tab 4: Navigatie (OSM & OSRM, no API key) ----------
with tabs[4]:
    st.markdown('<div class="tab-block">', unsafe_allow_html=True)
    st.header("🗺️ Navigatie (OpenStreetMap + OSRM) — geen API key")
    st.write("Voer een adres of `lat,lon` in. We gebruiken Nominatim (OSM) voor geocoding en OSRM public router voor route & instructies.")
    col1, col2 = st.columns(2)
    with col1:
        start_input = st.text_input("Start (adres or lat,lon)", "Amsterdam Centraal")
    with col2:
        end_input = st.text_input("Bestemming (adres or lat,lon)", "Rotterdam Centraal")
    if st.button("📍 Bereken route"):
        with st.spinner("Geocoding & route ophalen... (beleefd gebruik van OSM services)"):
            s_coord = geocode_address(start_input)
            time.sleep(0.8)  # be courteous
            e_coord = geocode_address(end_input)

            if not s_coord:
                st.error("Kon startlocatie niet vinden. Probeer een ander adres of gebruik lat,lon.")
            elif not e_coord:
                st.error("Kon bestemming niet vinden. Probeer een ander adres of gebruik lat,lon.")
            else:
                lat1, lon1 = s_coord
                lat2, lon2 = e_coord
                route = osrm_route(lat1, lon1, lat2, lon2)
                if not route:
                    st.error("Kon geen route ophalen van OSRM (beperkt/af en toe niet beschikbaar). Probeer later of kies andere locaties.")
                else:
                    # show stats
                    st.markdown(f"**Afstand:** {round(route['distance_m']/1000,2)} km — **Tijd:** {int(route['duration_s']//60)} min")
                    # create folium map centered
                    mid_lat = (lat1 + lat2) / 2
                    mid_lon = (lon1 + lon2) / 2
                    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=12, tiles="CartoDB dark_matter")
                    # add markers
                    folium.Marker([lat1, lon1], tooltip="Start", icon=folium.Icon(color="lightgray", icon="play")).add_to(m)
                    folium.Marker([lat2, lon2], tooltip="Bestemming", icon=folium.Icon(color="green", icon="flag")).add_to(m)
                    # add route
                    folium.GeoJson(route["geojson"], name="route",
                                   style_function=lambda x: {"color":"#1DB954", "weight":6, "opacity":0.9}).add_to(m)
                    # fit bounds if possible
                    try:
                        coords = route["geojson"]["coordinates"]
                        lats = [pt[1] for pt in coords]
                        lons = [pt[0] for pt in coords]
                        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
                    except Exception:
                        pass
                    st.markdown('<div class="folium-container">', unsafe_allow_html=True)
                    st_folium(m, width=920, height=470)
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.subheader("🚦 Turn-by-turn instructies")
                    for i, step in enumerate(route["steps"], 1):
                        st.markdown(f"**{i}.** {step['text']} — {int(step['distance_m'])} m")
    st.markdown('</div>', unsafe_allow_html=True)

# End of file
