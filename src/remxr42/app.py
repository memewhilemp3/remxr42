"""
WINAMP v2.91 - DUAL VINYL TURNTABLE DJ TABLE CONSOLE
[Circular Polar Spectrogram & 8-Bit Kirby's Pinball Edition]

Run with:
    python -m streamlit run dj_turntable_app.py --server.port 8502
"""

import os
import sys
import io
import base64
import importlib
import numpy as np
import soundfile as sf
import scipy.signal as sig
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

# Ensure local directory is on python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from remxr42 import spectrogram_engine as cse
    from remxr42 import console_component as tcc
except ImportError:
    try:
        import spectrogram_engine as cse
        import console_component as tcc
    except ImportError:
        import circular_spectrogram_engine as cse
        import turntable_console_component as tcc

# Page Setup
st.set_page_config(
    page_title="remxr42 - Dual Polar Vinyl Workstation",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Helper functions for Base64 assets
def pil_to_b64(img):
    if img is None:
        return ""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

def audio_to_b64_uri(audio, sr):
    if audio is None or len(audio) == 0:
        return ""
    # Clamp to max 24s and 22050 Hz for lightning fast web audio decoding
    max_dur = 24.0
    if len(audio) / float(sr) > max_dur:
        audio = audio[:int(max_dur * sr)]
    if sr > 24000:
        target_sr = 22050
        audio = sig.resample(audio, int(len(audio) * float(target_sr) / sr)).astype(np.float32)
        sr = target_sr
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:audio/wav;base64,{b64}"

def load_local_asset_b64(fname):
    p = os.path.join(current_dir, "kirby_web_assets", fname)
    if not os.path.exists(p):
        p = os.path.join(current_dir, fname)
    if os.path.exists(p):
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

main_win_b64 = load_local_asset_b64("kirby_main_window.png") or load_local_asset_b64("Kirby_Amp.png")

# Teenage Engineering Industrial Design Styling (EP-133 / EP-40 style)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Inter:wght@400;600;700;800;900&display=swap');

    .stApp {
        background-color: #141517 !important;
        background-image: radial-gradient(#222428 15%, transparent 16%) !important;
        background-size: 10px 10px !important;
        font-family: 'Space Mono', monospace !important;
        color: #1a1b1d !important;
    }

    header[data-testid="stHeader"] { background-color: transparent !important; }
    footer { display: none !important; }

    .remxr-chassis {
        background-color: #e5e2d9 !important;
        border: 1px solid #c7c3b6 !important;
        border-radius: 3px !important;
        box-shadow: 0 16px 36px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.9) !important;
        padding: 8px !important;
        margin-bottom: 8px !important;
    }

    .remxr-titlebar {
        background: #dad6cc !important;
        border-bottom: 2px solid #bab5a7 !important;
        border-radius: 1px !important;
        color: #121314 !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 11px !important;
        font-weight: bold !important;
        letter-spacing: 1px !important;
        padding: 6px 12px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-bottom: 6px !important;
    }

    div[data-baseweb="input"] {
        background-color: #181a1d !important;
        border: 1px solid #303338 !important;
        border-radius: 1px !important;
    }
    div[data-baseweb="input"] input {
        background-color: #181a1d !important;
        color: #00ff9d !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 11.5px !important;
    }

    .stButton > button {
        background: #f5f3ec !important;
        color: #1a1b1d !important;
        border: 1px solid #cdc9bb !important;
        border-radius: 1px !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 10px !important;
        padding: 5px 12px !important;
        box-shadow: 0 2.5px 0 #b3b0a2, 0 1px 2px rgba(0,0,0,0.12) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        transition: transform 0.05s, box-shadow 0.05s !important;
    }
    .stButton > button:hover {
        background: #ffffff !important;
    }
    .stButton > button:active {
        transform: translateY(1.5px) !important;
        box-shadow: 0 1px 0 #b3b0a2 !important;
    }

    /* Tabs Styling */
    div[data-baseweb="tab-list"] {
        background: #1c1e21 !important;
        padding: 4px !important;
        border-radius: 2px !important;
        border: 1px solid #2d3035 !important;
        gap: 6px !important;
    }
    button[data-baseweb="tab"] {
        background: transparent !important;
        color: #999 !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 11px !important;
        font-weight: bold !important;
        border-radius: 1px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: #ff4800 !important;
        color: #ffffff !important;
    }

    /* Radio Inputs */
    div[data-testid="stRadio"] label {
        font-family: 'Space Mono', monospace !important;
        font-size: 11px !important;
        color: #1a1b1d !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Presets & Independent Session State
# ---------------------------------------------------------------------------
PRESET_SPEC_URL = "https://dn710108.ca.archive.org/0/items/hybrid-theory-dolby-atmos-stems-linkin-park/Crawling%20%28DA%20Stem%201%29_spectrogram.png"
PRESET_YT_URL = "https://www.youtube.com/watch?v=Gd9OhYroLN0"

@st.cache_data(show_spinner=False, ttl=1800)
def cached_youtube_search(query: str, max_results: int = 3):
    return cse.search_youtube(query, max_results=max_results)

def pick_yt_track(deck_key, url, auto_load=False):
    st.session_state[f"yt_{deck_key}"] = url
    if auto_load:
        st.session_state[f"trigger_load_{deck_key}"] = True

def generate_default_deck(side="A"):
    sr = 22050
    duration = 4.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    if side == "A":
        # 120 BPM Synth Breakbeat / Lead
        kick = np.sin(2 * np.pi * 55 * np.exp(-4 * (t % 0.5))) * (t % 0.5 < 0.25)
        sweep = 0.3 * np.sin(2 * np.pi * (220 + 440 * np.sin(2 * np.pi * 0.5 * t)) * t)
        chord = 0.2 * (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 554.37 * t) + np.sin(2 * np.pi * 659.25 * t))
        audio = (kick + sweep + chord).astype(np.float32)
        name = "remxr42 Lead Loop A"
        cmap = "sox"
    else:
        # Sub-bass groove
        kick = np.sin(2 * np.pi * 55 * np.exp(-4 * (t % 0.5))) * (t % 0.5 < 0.25)
        bass = 0.4 * np.sin(2 * np.pi * 82.4 * t) * (1 + 0.3 * np.sin(2 * np.pi * 4 * t))
        hihat = 0.1 * np.random.uniform(-1, 1, size=len(t)) * (t % 0.25 < 0.05)
        audio = (kick + bass + hihat).astype(np.float32)
        name = "remxr42 Bass Groove B"
        cmap = "plasma"

    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.95

    label_art = cse.get_remxr42_label_art(None, size=150, side=side)
    vinyl_disc = cse.audio_to_circular_spectrogram((audio, sr), size=600, colormap=cmap, center_art=label_art)
    vinyl_b64 = pil_to_b64(vinyl_disc)

    mag, _, _ = cse.compute_stft_magnitude(audio, sr=sr)
    mag_db = cse.magnitude_to_db(mag)
    lin_img = cse.db_to_colored_image(mag_db, colormap=cmap)
    lin_b64 = pil_to_b64(lin_img)

    aud_b64 = audio_to_b64_uri(audio, sr)
    grid_disp = cse.render_grid_compass_display(None, width=280, height=180, title=name, sub_label=f"REMXR-42 // DECK {side}")
    grid_b64 = pil_to_b64(grid_disp)
    wf_disp = cse.render_backlit_waveform_display(audio, sr, width=320, height=80, title=f"REMXR-42 // DECK {side} WAVEFORM", color_theme="amber" if side == "A" else "mint")
    wf_b64 = pil_to_b64(wf_disp)
    return {
        "audio": audio,
        "sr": sr,
        "name": name,
        "audio_uri": aud_b64,
        "vinyl_uri": vinyl_b64,
        "linear_uri": lin_b64,
        "grid_b64": grid_b64,
        "waveform_b64": wf_b64,
        "duration": duration
    }

# Independent State Storage (Preload default remxr42 turntable discs)
if "deck_a_data" not in st.session_state or not st.session_state.deck_a_data.get("vinyl_uri"):
    st.session_state.deck_a_data = generate_default_deck(side="A")

if "deck_b_data" not in st.session_state or not st.session_state.deck_b_data.get("vinyl_uri"):
    st.session_state.deck_b_data = generate_default_deck(side="B")

if "trigger_load_a" not in st.session_state:
    st.session_state["trigger_load_a"] = False
if "trigger_load_b" not in st.session_state:
    st.session_state["trigger_load_b"] = False

# Main App Tabs
tab_table, tab_lab, tab_theory = st.tabs([
    "🎛️ REMXR42 WORKSTATION",
    "🔄 POLAR CONVERSION LAB",
    "📜 TIME-FREQUENCY ARCHITECTURE"
])

# ===========================================================================
# TAB 1: DUAL VINYL TURNTABLE DJ TABLE
# ===========================================================================
with tab_table:
    # ------------------ Media Ingestion Inputs ------------------
    col_in_a, col_in_b = st.columns(2)

    with col_in_a:
        st.markdown("""
        <div class="remxr-chassis" style="margin-bottom:4px;">
            <div class="remxr-titlebar" style="background: linear-gradient(90deg, #1b3a4b 0%, #0077b6 100%);">
                <span>LOAD DECK A (LEFT TURNTABLE)</span>
            </div>
        """, unsafe_allow_html=True)

        type_a = st.radio("Deck A Source", ["YouTube Link", "Archive.org Spectrogram", "Audio URL / File"], key="type_a", horizontal=True)
        if type_a == "YouTube Link":
            col_search_a, col_url_a = st.columns([1, 1])
            with col_search_a:
                q_a = st.text_input("🔍 Search YouTube Track", placeholder="e.g. Daft Punk, Gorillaz, Breakbeat...", key="q_a")
            with col_url_a:
                val_a = st.text_input("🔗 YouTube Video URL", key="yt_a")

            if q_a and q_a.strip():
                with st.spinner("Searching YouTube..."):
                    results_a = cached_youtube_search(q_a.strip(), max_results=3)
                if results_a:
                    st.markdown("<div style='background:#100d08; color:#ff8c00; padding:4px 8px; font-size:10px; border:1px solid #ff8c00; margin:4px 0; font-family:\"Space Mono\", monospace;'>■ REMXR-42 // BACKLIT SEARCH RESULTS:</div>", unsafe_allow_html=True)
                    for idx, itm in enumerate(results_a):
                        r_col1, r_col2, r_col3 = st.columns([1.2, 2.4, 1.4])
                        with r_col1:
                            grid_img = cse.render_grid_compass_display(itm['thumbnail'], width=180, height=115, title=itm['title'], sub_label="ELD 320x240")
                            st.image(grid_img, use_container_width=True)
                        with r_col2:
                            st.markdown(f"<div style='font-size:10.5px; font-weight:bold; color:#ff8c00; font-family:\"Space Mono\", monospace; line-height:1.2;'>{itm['title'][:44]}</div><div style='font-size:9px; color:#888; font-family:\"Space Mono\", monospace;'>{itm['uploader']} • ⏱️ {itm['duration_str']}</div>", unsafe_allow_html=True)
                        with r_col3:
                            st.button("Set URL", key=f"sel_a_{itm['id']}_{idx}", on_click=pick_yt_track, args=("a", itm['url'], False), use_container_width=True)
                            st.button("🚀 Load", key=f"load_a_{itm['id']}_{idx}", on_click=pick_yt_track, args=("a", itm['url'], True), use_container_width=True)
        elif type_a == "Archive.org Spectrogram":
            val_a = st.text_input("Spectrogram Image URL", value=PRESET_SPEC_URL, key="spec_a")
        else:
            val_a = st.text_input("Audio URL", value="https://archive.org/download/hybrid-theory-dolby-atmos-stems-linkin-park/Crawling%20%28DA%20Stem%201%29.mp3", key="aud_a")

        should_load_a = st.button("🚀 LOAD INTO DECK A TURNTABLE", key="btn_load_a", use_container_width=True) or st.session_state.pop("trigger_load_a", False)
        if should_load_a:
            with st.spinner("Streaming Deck A, cutting circular polar spectrogram grooves..."):
                try:
                    s_a = str(val_a).strip() if 'val_a' in locals() and val_a else ""
                    if not s_a and type_a == "YouTube Link" and 'q_a' in locals() and q_a and q_a.strip():
                        hits = cached_youtube_search(q_a.strip(), max_results=1)
                        if hits:
                            s_a = hits[0]['url']
                    if not s_a:
                        s_a = PRESET_YT_URL

                    if not cse.is_youtube_url(s_a) and not s_a.startswith("http") and not os.path.exists(s_a):
                        hits = cached_youtube_search(s_a, max_results=1)
                        if hits:
                            s_a = hits[0]['url']

                    thumb_a = None
                    if cse.is_youtube_url(s_a):
                        aud_a, sr_a, name_a, thumb_a = cse.load_audio_from_source(s_a)
                    elif any(s_a.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg"]) or "_spectrogram" in s_a.lower():
                        aud_a, sr_a = cse.circular_spectrogram_to_audio(s_a, target_duration_sec=14.0)
                        name_a = "Stem 1 Spectrogram"
                        thumb_a = s_a
                    else:
                        aud_a, sr_a, name_a, thumb_a = cse.load_audio_from_source(s_a)

                    yt_id = cse.extract_youtube_id(s_a)
                    thumb_src = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" if yt_id else (thumb_a or s_a)

                    # 1. Backlit Orange-on-Black Display
                    grid_disp_a = cse.render_grid_compass_display(thumb_src, width=280, height=180, title=name_a, sub_label="REMXR-42 // DECK A")
                    grid_b64_a = pil_to_b64(grid_disp_a)

                    # 1b. Backlit Waveform Display
                    wf_disp_a = cse.render_backlit_waveform_display(aud_a, sr_a, width=320, height=80, title=f"DECK A // {name_a[:20]}", color_theme="amber")
                    wf_b64_a = pil_to_b64(wf_disp_a)

                    # 2. remxr42 Industrial Vinyl Label Art (Side A) with Amber Center
                    remxr_label_a = cse.get_remxr42_label_art(thumb_src, size=150, side="A")

                    # 3. Circular Polar Vinyl Spectrogram
                    vinyl_disc = cse.audio_to_circular_spectrogram((aud_a, sr_a), size=600, colormap="sox", center_art=remxr_label_a)
                    vinyl_b64 = pil_to_b64(vinyl_disc)

                    # 4. Linear Spectrogram for strip
                    mag, _, _ = cse.compute_stft_magnitude(aud_a, sr=sr_a)
                    mag_db = cse.magnitude_to_db(mag)
                    lin_img = cse.db_to_colored_image(mag_db, colormap="sox")
                    lin_b64 = pil_to_b64(lin_img)

                    # 5. Audio URI
                    aud_b64 = audio_to_b64_uri(aud_a, sr_a)
                    dur_a = len(aud_a) / float(sr_a)

                    st.session_state.deck_a_data.update({
                        "audio": aud_a,
                        "sr": sr_a,
                        "name": name_a,
                        "audio_uri": aud_b64,
                        "vinyl_uri": vinyl_b64,
                        "linear_uri": lin_b64,
                        "grid_b64": grid_b64_a,
                        "waveform_b64": wf_b64_a,
                        "duration": dur_a
                    })
                    st.success(f"● DECK A ARMED: {name_a} ({dur_a:.1f}s)")
                except Exception as ex:
                    st.error(f"Deck A Load Error: {ex}")

        # REMXR-42 Optical Telemetry Monitor for Deck A
        da_cur = st.session_state.deck_a_data
        st.markdown(f"""
        <div style="background:#0c0a08; border:2px solid #332b22; border-radius:6px; padding:6px; margin-top:6px; box-shadow:0 4px 12px rgba(0,0,0,0.6), inset 0 0 10px rgba(255,140,0,0.12);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #221c16; padding-bottom:3px; margin-bottom:5px;">
                <span style="font-family:'Space Mono', monospace; font-size:9.5px; font-weight:bold; color:#ff8c00; letter-spacing:0.5px;">
                    ■ REMXR-42 // OPTICAL TELEMETRY MONITOR (DECK A)
                </span>
                <span style="font-family:'Space Mono', monospace; font-size:8.5px; color:#ff8c00; background:#1c1000; padding:1px 5px; border-radius:3px; border:1px solid #ff8c00;">
                    ARMED • 33 RPM
                </span>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                <img src="{da_cur.get('grid_b64', '')}" style="width:105px; height:72px; border:1px solid #ff8c00; border-radius:2px; box-shadow:0 0 6px rgba(255,140,0,0.35); object-fit:cover;"/>
                <img src="{da_cur.get('waveform_b64', '')}" style="width:160px; height:72px; border:1px solid #ff8c00; border-radius:2px; box-shadow:0 0 6px rgba(255,140,0,0.35); object-fit:cover;"/>
                <div style="flex:1; font-family:'Space Mono', monospace; font-size:9.5px; color:#ffa500; line-height:1.35;">
                    <div style="font-size:11px; font-weight:bold; color:#ffffff; text-shadow:0 0 3px #ff8c00;">{da_cur['name'][:30]}</div>
                    <div style="color:#cc7700; margin-top:2px;">STATUS: <span style="color:#00ff9d; font-weight:bold;">READY TO SCRATCH</span></div>
                    <div style="color:#995500;">LENGTH: {da_cur['duration']:.1f}s • {da_cur['sr']} Hz</div>
                    <div style="color:#663300; font-size:8px; margin-top:2px;">REMXR-42 // ELECTROLUMINESCENT FLAT PANEL</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_in_b:
        st.markdown("""
        <div class="remxr-chassis" style="margin-bottom:4px;">
            <div class="remxr-titlebar" style="background: linear-gradient(90deg, #0a3d31 0%, #1b4332 100%);">
                <span>LOAD DECK B (RIGHT TURNTABLE)</span>
            </div>
        """, unsafe_allow_html=True)

        type_b = st.radio("Deck B Source", ["120BPM Sub-Bass Groove", "YouTube Link", "Archive.org Spectrogram", "Audio URL / File"], key="type_b", horizontal=True)
        if type_b == "120BPM Sub-Bass Groove":
            st.info("Generates an electronic sub-bass groove to blend with Deck A.")
            val_b = "synth"
        elif type_b == "YouTube Link":
            col_search_b, col_url_b = st.columns([1, 1])
            with col_search_b:
                q_b = st.text_input("🔍 Search YouTube Track", placeholder="e.g. Chemical Brothers, Prodigy, Amen Break...", key="q_b")
            with col_url_b:
                val_b = st.text_input("🔗 YouTube Video URL", key="yt_b", placeholder="https://www.youtube.com/watch?v=...")

            if q_b and q_b.strip():
                with st.spinner("Searching YouTube..."):
                    results_b = cached_youtube_search(q_b.strip(), max_results=3)
                if results_b:
                    st.markdown("<div style='background:#100d08; color:#ff8c00; padding:4px 8px; font-size:10px; border:1px solid #ff8c00; margin:4px 0; font-family:\"Space Mono\", monospace;'>■ REMXR-42 // BACKLIT SEARCH RESULTS:</div>", unsafe_allow_html=True)
                    for idx, itm in enumerate(results_b):
                        r_col1, r_col2, r_col3 = st.columns([1.2, 2.4, 1.4])
                        with r_col1:
                            grid_img_b = cse.render_grid_compass_display(itm['thumbnail'], width=180, height=115, title=itm['title'], sub_label="ELD 320x240")
                            st.image(grid_img_b, use_container_width=True)
                        with r_col2:
                            st.markdown(f"<div style='font-size:10.5px; font-weight:bold; color:#ff8c00; font-family:\"Space Mono\", monospace; line-height:1.2;'>{itm['title'][:44]}</div><div style='font-size:9px; color:#888; font-family:\"Space Mono\", monospace;'>{itm['uploader']} • ⏱️ {itm['duration_str']}</div>", unsafe_allow_html=True)
                        with r_col3:
                            st.button("Set URL", key=f"sel_b_{itm['id']}_{idx}", on_click=pick_yt_track, args=("b", itm['url'], False), use_container_width=True)
                            st.button("🚀 Load", key=f"load_b_{itm['id']}_{idx}", on_click=pick_yt_track, args=("b", itm['url'], True), use_container_width=True)
        elif type_b == "Archive.org Spectrogram":
            val_b = st.text_input("Spectrogram Image URL", value="https://dn710108.ca.archive.org/0/items/hybrid-theory-dolby-atmos-stems-linkin-park/Crawling%20%28DA%20Stem%202%29_spectrogram.png", key="spec_b")
        else:
            val_b = st.text_input("Audio URL", value="https://archive.org/download/hybrid-theory-dolby-atmos-stems-linkin-park/Crawling%20%28DA%20Stem%202%29.mp3", key="aud_b")

        should_load_b = st.button("🚀 LOAD INTO DECK B TURNTABLE", key="btn_load_b", use_container_width=True) or st.session_state.pop("trigger_load_b", False)
        if should_load_b:
            with st.spinner("Processing Deck B, cutting circular vinyl spectrogram grooves..."):
                try:
                    s_b = str(val_b).strip() if 'val_b' in locals() and val_b else ""
                    if not s_b and type_b == "YouTube Link" and 'q_b' in locals() and q_b and q_b.strip():
                        hits = cached_youtube_search(q_b.strip(), max_results=1)
                        if hits:
                            s_b = hits[0]['url']
                    if not s_b and type_b != "120BPM Sub-Bass Groove":
                        s_b = "https://www.youtube.com/watch?v=wmin5WkOuPw"

                    thumb_b = None
                    if type_b == "120BPM Sub-Bass Groove" or s_b == "synth":
                        sr_b = 22050
                        t = np.linspace(0, 8.0, int(8.0 * sr_b), False)
                        kick = np.sin(2 * np.pi * 55 * np.exp(-t % 0.5 * 16) * t) * np.exp(-t % 0.5 * 9)
                        bass = 0.5 * np.sin(2 * np.pi * 82.4 * t) * (1 + 0.3 * np.sin(2 * np.pi * 4 * t))
                        aud_b = (kick + bass).astype(np.float32)
                        aud_b /= np.max(np.abs(aud_b))
                        name_b = "120BPM Sub-Bass Groove"
                        thumb_src_b = None
                    elif cse.is_youtube_url(s_b):
                        aud_b, sr_b, name_b, thumb_b = cse.load_audio_from_source(s_b)
                        yt_id_b = cse.extract_youtube_id(s_b)
                        thumb_src_b = f"https://img.youtube.com/vi/{yt_id_b}/hqdefault.jpg" if yt_id_b else thumb_b
                    elif any(s_b.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg"]) or "_spectrogram" in s_b.lower():
                        aud_b, sr_b = cse.circular_spectrogram_to_audio(s_b, target_duration_sec=14.0)
                        name_b = "Stem 2 Spectrogram"
                        thumb_src_b = s_b
                    else:
                        if not s_b.startswith("http") and not os.path.exists(s_b):
                            hits = cached_youtube_search(s_b, max_results=1)
                            if hits:
                                s_b = hits[0]['url']
                        aud_b, sr_b, name_b, thumb_b = cse.load_audio_from_source(s_b)
                        thumb_src_b = thumb_b or s_b

                    # 1. Backlit Display (Side B)
                    grid_disp_b = cse.render_grid_compass_display(thumb_src_b, width=280, height=180, title=name_b, sub_label="REMXR-42 // DECK B")
                    grid_b64_b = pil_to_b64(grid_disp_b)

                    # 1b. Backlit Waveform Display (Side B - Mint Theme)
                    wf_disp_b = cse.render_backlit_waveform_display(aud_b, sr_b, width=320, height=80, title=f"DECK B // {name_b[:20]}", color_theme="mint")
                    wf_b64_b = pil_to_b64(wf_disp_b)

                    # 2. remxr42 Industrial Vinyl Label Art (Side B)
                    remxr_label_b = cse.get_remxr42_label_art(thumb_src_b, size=150, side="B")

                    # 3. Circular Vinyl Spectrogram
                    vinyl_disc_b = cse.audio_to_circular_spectrogram((aud_b, sr_b), size=600, colormap="plasma", center_art=remxr_label_b)
                    vinyl_b64_b = pil_to_b64(vinyl_disc_b)

                    # 4. Linear Spectrogram
                    mag_b, _, _ = cse.compute_stft_magnitude(aud_b, sr=sr_b)
                    mag_db_b = cse.magnitude_to_db(mag_b)
                    lin_img_b = cse.db_to_colored_image(mag_db_b, colormap="plasma")
                    lin_b64_b = pil_to_b64(lin_img_b)

                    # 5. Audio URI
                    aud_b64_b = audio_to_b64_uri(aud_b, sr_b)
                    dur_b = len(aud_b) / float(sr_b)

                    st.session_state.deck_b_data.update({
                        "audio": aud_b,
                        "sr": sr_b,
                        "name": name_b,
                        "audio_uri": aud_b64_b,
                        "vinyl_uri": vinyl_b64_b,
                        "linear_uri": lin_b64_b,
                        "grid_b64": grid_b64_b,
                        "waveform_b64": wf_b64_b,
                        "duration": dur_b
                    })
                    st.success(f"● DECK B ARMED: {name_b} ({dur_b:.1f}s)")
                except Exception as ex:
                    st.error(f"Deck B Load Error: {ex}")

        # REMXR-42 Optical Telemetry Monitor for Deck B
        db_cur = st.session_state.deck_b_data
        st.markdown(f"""
        <div style="background:#0c0a08; border:2px solid #223328; border-radius:6px; padding:6px; margin-top:6px; box-shadow:0 4px 12px rgba(0,0,0,0.6), inset 0 0 10px rgba(0,255,157,0.10);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #16221c; padding-bottom:3px; margin-bottom:5px;">
                <span style="font-family:'Space Mono', monospace; font-size:9.5px; font-weight:bold; color:#00ff9d; letter-spacing:0.5px;">
                    ■ REMXR-42 // OPTICAL TELEMETRY MONITOR (DECK B)
                </span>
                <span style="font-family:'Space Mono', monospace; font-size:8.5px; color:#00ff9d; background:#001c12; padding:1px 5px; border-radius:3px; border:1px solid #00ff9d;">
                    ARMED • 33 RPM
                </span>
            </div>
            <div style="display:flex; gap:8px; align-items:center;">
                <img src="{db_cur.get('grid_b64', '')}" style="width:105px; height:72px; border:1px solid #00ff9d; border-radius:2px; box-shadow:0 0 6px rgba(0,255,157,0.35); object-fit:cover;"/>
                <img src="{db_cur.get('waveform_b64', '')}" style="width:160px; height:72px; border:1px solid #00ff9d; border-radius:2px; box-shadow:0 0 6px rgba(0,255,157,0.35); object-fit:cover;"/>
                <div style="flex:1; font-family:'Space Mono', monospace; font-size:9.5px; color:#55ffbb; line-height:1.35;">
                    <div style="font-size:11px; font-weight:bold; color:#ffffff; text-shadow:0 0 3px #00ff9d;">{db_cur['name'][:30]}</div>
                    <div style="color:#00cc7a; margin-top:2px;">STATUS: <span style="color:#00ff9d; font-weight:bold;">READY TO SCRATCH</span></div>
                    <div style="color:#009955;">LENGTH: {db_cur['duration']:.1f}s • {db_cur['sr']} Hz</div>
                    <div style="color:#006633; font-size:8px; margin-top:2px;">REMXR-42 // ELECTROLUMINESCENT FLAT PANEL</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------ Dual Turntable DJ Console Component ------------------
    da = st.session_state.deck_a_data
    db = st.session_state.deck_b_data

    html_code = tcc.get_turntable_console_component(
        audio_a_uri=da["audio_uri"],
        sr_a=da["sr"],
        name_a=da["name"],
        vinyl_a_uri=da["vinyl_uri"],
        linear_spec_a_uri=da["linear_uri"],
        grid_a_uri=da.get("grid_b64", ""),
        audio_b_uri=db["audio_uri"],
        sr_b=db["sr"],
        name_b=db["name"],
        vinyl_b_uri=db["vinyl_uri"],
        linear_spec_b_uri=db["linear_uri"],
        grid_b_uri=db.get("grid_b64", "")
    )

    # Embed Turntable DJ Table Component in Streamlit
    components.html(html_code, height=740, scrolling=True)


# ===========================================================================
# TAB 2: CONVERSION LAB (Circular Spectrogram <--> Audio)
# ===========================================================================
with tab_lab:
    st.markdown("""
    <div class="remxr-chassis">
        <div class="remxr-titlebar">
            <span>CIRCULAR SPECTROGRAM ⇄ AUDIO CONVERSION LAB</span>
        </div>
    """, unsafe_allow_html=True)

    col_lab1, col_lab2 = st.columns(2)

    with col_lab1:
        st.markdown("#### 💿 Circular Polar Spectrogram Image ➔ Audio WAV")
        st.caption("Unwraps circular polar disc to Cartesian STFT magnitude and reconstructs phase via Griffin-Lim.")

        c_spec_input = st.text_input("Circular Vinyl Image URL or Path", value=os.path.join(current_dir, "test_circular_vinyl.png"))
        col_gl_iter, col_gl_dur = st.columns(2)
        with col_gl_iter:
            gl_iters = st.slider("Griffin-Lim Iterations", 8, 48, 20, step=4)
        with col_gl_dur:
            target_sec = st.slider("Target Duration (seconds)", 2.0, 30.0, 6.0, step=1.0)

        if st.button("🔊 SYNTHESIZE AUDIO FROM CIRCULAR VINYL", use_container_width=True):
            with st.spinner("Unwrapping polar disc and synthesizing audio via Griffin-Lim..."):
                try:
                    rec_aud, rec_sr = cse.circular_spectrogram_to_audio(
                        c_spec_input,
                        sample_rate=22050,
                        n_iter=gl_iters,
                        target_duration_sec=target_sec
                    )
                    buf = io.BytesIO()
                    sf.write(buf, rec_aud, rec_sr, format="WAV")
                    st.success(f"Synthesized {len(rec_aud)/rec_sr:.2f}s audio at {rec_sr} Hz!")
                    st.audio(buf.getvalue(), format="audio/wav")
                    st.download_button("💾 Download Synthesized WAV", buf.getvalue(), "circular_synthesized.wav", "audio/wav")
                except Exception as ex:
                    st.error(f"Synthesis error: {ex}")

    with col_lab2:
        st.markdown("#### 🔊 Audio File / YouTube ➔ Circular Vinyl Spectrogram")
        st.caption("Transforms time-frequency STFT into a spinning polar vinyl record with groove texture and remxr42 center label.")

        c_aud_input = st.text_input("Audio URL or YouTube Link", value=PRESET_YT_URL, key="lab_aud_input")
        cmap_sel = st.selectbox("Colormap", ["sox", "plasma"])
        disc_size = st.slider("Disc Diameter (pixels)", 400, 1000, 600, step=50)

        if st.button("💿 GENERATE CIRCULAR VINYL SPECTROGRAM", use_container_width=True):
            with st.spinner("Calculating STFT and mapping polar vinyl grooves..."):
                try:
                    if cse.is_youtube_url(c_aud_input):
                        aud_data, sr_val, title_val, thumb_val = cse.load_audio_from_source(c_aud_input)
                    else:
                        aud_data, sr_val, title_val, thumb_val = cse.load_audio_from_source(c_aud_input)

                    remxr_center = cse.get_remxr42_label_art(thumb_val, size=150, side="A")
                    vinyl_out = cse.audio_to_circular_spectrogram((aud_data, sr_val), size=disc_size, colormap=cmap_sel, center_art=remxr_center)
                    
                    st.image(vinyl_out, caption=f"Circular Vinyl Spectrogram: {title_val}", use_container_width=False, width=380)

                    buf_png = io.BytesIO()
                    vinyl_out.save(buf_png, format="PNG")
                    st.download_button("💾 Download Vinyl Spectrogram PNG", buf_png.getvalue(), "circular_vinyl_spectrogram.png", "image/png")
                except Exception as ex:
                    st.error(f"Error generating circular vinyl: {ex}")

    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# TAB 3: POLAR TIME-FREQUENCY THEORY & TOUCHDESIGNER TECHNIQUES
# ===========================================================================
with tab_theory:
    st.markdown("""
    <div class="remxr-chassis">
        <div class="remxr-titlebar">
            <span>POLAR SPECTROGRAM MATHEMATICS & TOUCHDESIGNER CONCEPTS</span>
        </div>
        <div style="background:#fff; padding:12px; font-size:12px; line-height:1.6; color:#000;">
            <h3>1. The Geometry of Circular Vinyl Spectrograms</h3>
            <p>
                In a traditional linear spectrogram, the horizontal axis represents <b>Time ($t$)</b> and the vertical axis represents <b>Frequency ($f$)</b>:
            </p>
            <pre style="background:#eee; padding:6px;">S(t, f) : t ∈ [0, T], f ∈ [0, f_max]</pre>
            <p>
                In a <b>Circular Vinyl Spectrogram</b>, Cartesian coordinates $(t, f)$ are mapped into Polar coordinates $(r, θ)$ centered at $(x_c, y_c)$:
            </p>
            <ul>
                <li><b>Angle $\\theta$ (Time)</b>: Full rotation around the disc maps time $t \\in [0, T]$ to angular displacement $\\theta \\in [0, 2\\pi)$. 12 o'clock represents $t = 0$.</li>
                <li><b>Radius $r$ (Frequency)</b>: The distance from the center label ($R_{{inner}}$) to the outer rim ($R_{{outer}}$) maps frequency $f \\in [0, f_{{max}}]$. Low bass frequencies vibrate near the center label, while crisp high frequencies reside on the outer rim.</li>
            </ul>

            <hr style="margin:10px 0;"/>

            <h3>2. Angular Splicing & Loop Boundaries</h3>
            <p>
                Instead of dragging linear vertical slice lines, circular splicing defines loop bounds as <b>angular pie wedges</b>:
            </p>
            <pre style="background:#eee; padding:6px;">
θ_in = (t_in / T) · 2π - π/2
θ_out = (t_out / T) · 2π - π/2
Active Slice Wedge = { (r, θ) | R_inner ≤ r ≤ R_outer,  θ_in ≤ θ ≤ θ_out }
            </pre>
            <p>
                As the turntable spins at 33⅓ RPM, the playhead needle passes through this highlighted sector, providing seamless, cyclical time looping.
            </p>

            <hr style="margin:10px 0;"/>

            <h3>3. How TouchDesigner Approaches This</h3>
            <p>
                In TouchDesigner (such as in visualizer project networks like <code>bloop_yt.2.toe</code>), polar remaps are typically implemented using:
            </p>
            <ol>
                <li><b>Audio Device In CHOP / Audio File In CHOP</b>: Captures multi-channel live audio or video streams.</li>
                <li><b>Audio Spectrum CHOP</b>: Computes real-time FFT frequency bin magnitudes.</li>
                <li><b>CHOP to TOP</b>: Converts the 1D frequency array into a 2D scrolling texture (spectrogram).</li>
                <li><b>Remap TOP with Polar UV Coordinates</b> (or a custom <b>GLSL TOP</b>):
                    Samples the linear spectrogram texture using polar coordinate transformation:
                    <code>vec2 uv_polar = vec2(atan(p.y, p.x) / (2.0 * PI), length(p));</code>
                </li>
            </ol>
            <p>
                Our Python & HTML5 Web Audio implementation achieves this exact polar transformation natively in pure vectorized NumPy (via <code>scipy.ndimage.map_coordinates</code>) and client-side HTML5 Canvas at 60 FPS, with full bidirectional round-trip synthesis back into audio WAV via the Griffin-Lim algorithm.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
