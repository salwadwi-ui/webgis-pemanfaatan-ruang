import os
import io
import time
import zipfile
import tempfile
import pathlib
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import leafmap.foliumap as leafmap

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account

# ─── GOOGLE DRIVE SETUP ──────────────────────────────────────
SCOPES    = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = st.secrets["FOLDER_ID"]

TEMP_DIR = pathlib.Path(tempfile.gettempdir()) / "webgis_cache"
TEMP_DIR.mkdir(exist_ok=True)

DATA_FILE       = TEMP_DIR / "data tugas akhir.geojson"
KABUPATEN_FILE  = TEMP_DIR / "Batas Administrasi Kabupaten Bandung.geojson"
KECAMATAN_FILE  = TEMP_DIR / "Batas Administrasi Kecamatan Katapang.geojson"
RTRW_FILE       = TEMP_DIR / "RTRW.geojson"

# ─── KONFIGURASI ─────────────────────────────────────────────
APP_TITLE      = "WebGIS Rekomendasi Teknis Pemanfaatan Ruang"
APP_SUBTITLE   = "Platform interaktif untuk publikasi data spasial dan pembaruan data teknis berbasis SHP oleh admin."
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")

st.set_page_config(
    page_title="Rekomendasi Teknis Pemanfaatan Ruang",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS MOBILE-FRIENDLY ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── BASE ── */
.stApp {
    background: linear-gradient(160deg, #f8fafc 0%, #eef4fa 50%, #ffffff 100%) !important;
    color: #25364a;
}

/* ── ANIMATIONS ── */
@keyframes fadeInUp  { from { opacity: 0; transform: translateY(22px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeIn    { from { opacity: 0; } to { opacity: 1; } }
@keyframes float     { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@keyframes dot-bounce{ 0%,80%,100% { transform: scale(0.5); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
@keyframes bar-grow  { from { width: 0; } }
@keyframes scan-line { 0% { top: 0%; } 100% { top: 100%; } }

.page-enter          { animation: fadeInUp 0.55s cubic-bezier(.22,1,.36,1) both; }
.page-enter-delay-1  { animation-delay: 0.05s; }
.page-enter-delay-2  { animation-delay: 0.12s; }
.page-enter-delay-3  { animation-delay: 0.19s; }
.page-enter-delay-4  { animation-delay: 0.26s; }

/* ── LOADING ── */
.loading-screen      { position:fixed;inset:0;z-index:9999;background:linear-gradient(160deg,#f8fafc,#eef4fa);display:flex;flex-direction:column;align-items:center;justify-content:center; }
.loading-logo        { font-size:3rem;animation:float 2s ease-in-out infinite;margin-bottom:20px; }
.loading-title       { font-size:1.3rem;font-weight:800;color:#4c7aaa;margin-bottom:6px; }
.loading-sub         { font-size:0.82rem;color:#68798d;margin-bottom:32px;text-align:center;padding:0 20px; }
.loading-bar-wrap    { width:220px;height:3px;background:rgba(104,121,141,0.12);border-radius:99px;overflow:hidden;margin-bottom:24px; }
.loading-bar         { height:100%;width:0;background:linear-gradient(90deg,#4c7aaa,#f4be6b);border-radius:99px;animation:bar-grow 1.8s cubic-bezier(.4,0,.2,1) forwards;animation-delay:0.2s; }
.loading-dots        { display:flex;gap:8px; }
.loading-dot         { width:7px;height:7px;border-radius:50%;background:#4c7aaa;animation:dot-bounce 1.2s ease-in-out infinite; }
.loading-dot:nth-child(2) { animation-delay:0.2s; }
.loading-dot:nth-child(3) { animation-delay:0.4s; }

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8fafc, #eef4fa) !important;
    border-right: 1px solid rgba(76,122,170,0.14) !important;
}
section[data-testid="stSidebar"] * { color: #25364a !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    background: linear-gradient(135deg, #4c7aaa, #5a88b7) !important;
    border: 1px solid rgba(76,122,170,0.35) !important;
    border-radius: 12px !important;
    margin: 0 !important;
    padding: 14px 16px !important;
    box-shadow: 0 6px 18px rgba(76,122,170,0.12) !important;
    box-sizing: border-box !important;
    width: 100% !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    cursor: pointer !important;
    min-height: 54px !important;
    height: 54px !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:last-child {
    flex: 1 !important;
    display: flex !important;
    align-items: center !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label p,
section[data-testid="stSidebar"] div[role="radiogroup"] label span,
section[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
    font-size: 13.5px !important;
    font-weight: 600 !important;
    color: #ffffff !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

/* ── HERO ── */
.hero-box {
    background: linear-gradient(135deg, #4c7aaa, #68798d, #7a8799);
    border-radius: 16px;
    padding: 24px 22px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
    animation: fadeInUp 0.6s cubic-bezier(.22,1,.36,1) both;
    box-shadow: 0 18px 40px rgba(76,122,170,0.12);
}
.hero-scan {
    position: absolute;
    left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(244,190,107,0.45), transparent);
    animation: scan-line 4s linear infinite;
    pointer-events: none;
}
.hero-title {
    font-size: 1.6rem;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 10px;
    background: linear-gradient(135deg, #ffffff, #fff5df, #f4be6b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-subtitle {
    font-size: 0.88rem;
    color: rgba(255,255,255,0.88);
    max-width: 620px;
    line-height: 1.65;
}
.mini-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 99px;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.24);
    color: #ffffff;
    font-weight: 700;
    font-size: 0.72rem;
    margin-bottom: 12px;
}

/* ── CARDS ── */
.info-card {
    background: rgba(255,255,255,0.92);
    border: 1px solid rgba(76,122,170,0.14);
    border-radius: 14px;
    padding: 18px 16px;
    margin-bottom: 14px;
    transition: all 0.2s;
    box-shadow: 0 10px 28px rgba(76,122,170,0.06);
}
.info-card:hover { border-color: rgba(76,122,170,0.28); transform: translateY(-2px); }
.section-title { font-size: 0.95rem; font-weight: 700; color: #4c7aaa; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }

.info-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid rgba(104,121,141,0.10); }
.info-item:last-child { border-bottom: none; padding-bottom: 0; }
.info-item-icon { width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 0.95rem; flex-shrink: 0; }
.info-item-text .title { font-size: 0.85rem; font-weight: 700; color: #25364a; margin-bottom: 2px; }
.info-item-text .desc  { font-size: 0.77rem; color: #68798d; line-height: 1.5; }

/* ── METRIC ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.96) !important;
    border: 1px solid rgba(76,122,170,0.14) !important;
    border-radius: 12px !important;
    padding: 14px 12px !important;
    box-shadow: 0 8px 24px rgba(76,122,170,0.06) !important;
}
[data-testid="stMetricLabel"] { font-size: 10px !important; font-weight: 700 !important; color: #68798d !important; text-transform: uppercase !important; letter-spacing: 0.7px !important; }
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 800 !important; color: #4c7aaa !important; }

/* ── BUTTON ── */
.stButton > button {
    background: linear-gradient(135deg, #4c7aaa, #5d8dbe) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    padding: 10px 20px !important;
    transition: all 0.2s !important;
    box-shadow: 0 6px 16px rgba(76,122,170,0.18) !important;
    width: 100% !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; }

/* ── INPUTS ── */
.stTextInput > div > div > input,
.stTextArea > div > textarea,
.stNumberInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid rgba(104,121,141,0.18) !important;
    border-radius: 10px !important;
    color: #25364a !important;
    font-size: 14px !important;
    padding: 10px 12px !important;
}
.stTextInput label, .stSelectbox label, .stTextArea label, .stNumberInput label {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #68798d !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
.stSelectbox > div > div {
    background: #ffffff !important;
    border: 1px solid rgba(104,121,141,0.18) !important;
    border-radius: 10px !important;
    font-size: 14px !important;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] { background: rgba(76,122,170,0.08) !important; border-radius: 11px !important; padding: 4px !important; overflow-x: auto !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; border-radius: 8px !important; color: #68798d !important; font-weight: 700 !important; font-size: 12px !important; padding: 8px 12px !important; white-space: nowrap !important; }
.stTabs [aria-selected="true"] { background: rgba(76,122,170,0.16) !important; color: #4c7aaa !important; }

/* ── ADMIN BOX ── */
.admin-box { background: rgba(255,255,255,0.95); border: 1px solid rgba(76,122,170,0.22); border-left: 4px solid #4c7aaa; border-radius: 12px; padding: 14px 16px; margin-bottom: 14px; color: #31587f; font-size: 13px; font-weight: 500; }
.upload-note { background: rgba(244,190,107,0.12); border: 1px solid rgba(244,190,107,0.26); border-left: 4px solid #f4be6b; border-radius: 10px; padding: 12px 14px; margin: 10px 0; font-size: 12px; color: #8a6117; line-height: 1.6; }

/* ── SIDEBAR BRAND ── */
.sidebar-brand { background: linear-gradient(135deg, rgba(76,122,170,0.12), rgba(244,190,107,0.12)); border: 1px solid rgba(76,122,170,0.18); border-radius: 14px; padding: 16px; margin-bottom: 16px; }
.sidebar-brand-title { font-size: 1rem; font-weight: 800; color: #4c7aaa; margin-bottom: 4px; }
.sidebar-brand-subtitle { font-size: 0.76rem; color: #68798d; line-height: 1.5; }
.sidebar-mini-card { background: rgba(255,255,255,0.82); border: 1px solid rgba(76,122,170,0.12); border-radius: 12px; padding: 14px; margin-top: 14px; }
.sidebar-mini-title { font-size: 0.73rem; font-weight: 800; color: #68798d; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.7px; }
.sidebar-stat { color: #5f6f83; font-size: 0.84rem; margin-bottom: 7px; }
.sidebar-note { color: #68798d; font-size: 0.76rem; line-height: 1.55; }

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.88) !important;
    border: 2px dashed rgba(76,122,170,0.24) !important;
    border-radius: 13px !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #c8d6e3; border-radius: 99px; }

/* ══════════════════════════════════════════
   MOBILE RESPONSIVE — max-width: 768px
══════════════════════════════════════════ */
@media (max-width: 768px) {
    .hero-box { padding: 18px 16px; border-radius: 12px; margin-bottom: 14px; }
    .hero-title { font-size: 1.25rem !important; }
    .hero-subtitle { font-size: 0.8rem; }
    .sidebar-brand-subtitle { display: none; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { font-size: 9px !important; }
    .alur-grid { grid-template-columns: repeat(2, 1fr) !important; gap: 8px !important; }
    .alur-item { padding: 12px 8px !important; }
    .alur-item-icon { font-size: 1.2rem !important; margin-bottom: 4px !important; }
    .alur-item-title { font-size: 0.73rem !important; }
    .alur-item-desc { font-size: 0.66rem !important; }
    .status-grid { flex-direction: column; gap: 8px; }
    .info-card { padding: 14px 12px; border-radius: 12px; }
    .section-title { font-size: 0.88rem; }
    .info-item { gap: 8px; padding: 8px 0; }
    .info-item-icon { width: 30px; height: 30px; font-size: 0.85rem; border-radius: 8px; }
    .info-item-text .title { font-size: 0.8rem; }
    .info-item-text .desc  { font-size: 0.72rem; }
    .two-col-mobile { grid-template-columns: 1fr !important; }
    .stSelectbox > div > div { min-height: 44px !important; font-size: 14px !important; }
    .stCaption { font-size: 11px !important; }
    .stTabs [data-baseweb="tab-list"] { flex-wrap: nowrap !important; }
}

@media (max-width: 480px) {
    .hero-title { font-size: 1.1rem !important; }
    .alur-grid  { grid-template-columns: 1fr 1fr !important; }
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "app_loaded" not in st.session_state:
    st.session_state.app_loaded = False

# ─── LOADING SCREEN ──────────────────────────────────────────
def show_loading():
    ph = st.empty()
    ph.markdown("""
    <div class="loading-screen">
        <div class="loading-logo">🗺️</div>
        <div class="loading-title">WebGIS Pemanfaatan Ruang</div>
        <div class="loading-sub">Memuat sistem informasi geografis…</div>
        <div class="loading-bar-wrap"><div class="loading-bar"></div></div>
        <div class="loading-dots">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(1.5)
    ph.empty()

# ─── GOOGLE DRIVE FUNCTIONS ──────────────────────────────────
@st.cache_resource
def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

def get_file_id(service, filename: str):
    """Cari file di folder Drive berdasarkan nama."""
    results = service.files().list(
        q=f"name='{filename}' and '{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None

def download_from_drive(service, filename: str, dest_path: pathlib.Path) -> bool:
    """Download file dari Drive ke lokal."""
    file_id = get_file_id(service, filename)
    if not file_id:
        return False
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return True

def upload_to_drive(service, local_path: pathlib.Path, filename: str):
    """Upload atau update file ke Google Drive."""
    file_id = get_file_id(service, filename)
    media   = MediaFileUpload(str(local_path), mimetype="application/geo+json", resumable=True)
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": filename, "parents": [FOLDER_ID]}
        service.files().create(body=metadata, media_body=media).execute()

# ─── INISIALISASI DRIVE & DOWNLOAD FILE ──────────────────────
drive_service = get_drive_service()

FILE_MAP = {
    "data tugas akhir.geojson"                      : DATA_FILE,
    "Batas Administrasi Kabupaten Bandung.geojson"  : KABUPATEN_FILE,
    "Batas Administrasi Kecamatan Katapang.geojson" : KECAMATAN_FILE,
    "RTRW.geojson"                                  : RTRW_FILE,
}

for fname, fpath in FILE_MAP.items():
    if not fpath.exists():
        download_from_drive(drive_service, fname, fpath)

# ─── LOAD DATA ───────────────────────────────────────────────
@st.cache_data(ttl=0)
def load_data():
    path = str(DATA_FILE)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        bounds = gdf.total_bounds
        gdf = gdf.set_crs("EPSG:3857" if abs(bounds[0]) > 180 or abs(bounds[2]) > 180 else "EPSG:4326")
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    if "OBJECTID" not in gdf.columns:
        gdf.insert(0, "OBJECTID", range(1, len(gdf) + 1))
    return gdf

@st.cache_data(ttl=0)
def load_boundary(filepath: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(filepath)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    gdf["geometry"] = gdf["geometry"].apply(
        lambda geom: geom if geom is None else geom.__class__(
            [(c[0], c[1]) for ring in (
                [geom.exterior] + list(geom.interiors)
                if hasattr(geom, 'exterior') else [geom]
            ) for c in ring.coords]
        ) if hasattr(geom, 'exterior') else geom
    )
    return gdf

def save_data(gdf: gpd.GeoDataFrame):
    """Simpan GeoDataFrame ke lokal lalu upload ke Google Drive."""
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    gdf.to_file(str(DATA_FILE), driver="GeoJSON")
    upload_to_drive(drive_service, DATA_FILE, "data tugas akhir.geojson")
    st.cache_data.clear()


def read_shp_from_zip(uploaded_zip) -> gpd.GeoDataFrame:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "up.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.read())
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmpdir)
        shp_files = list(Path(tmpdir).rglob("*.shp"))
        if not shp_files:
            raise ValueError("Tidak ada file .shp di dalam ZIP.")
        shp = gpd.read_file(str(shp_files[0]))
        if shp.crs is None:
            bounds = shp.total_bounds
            if abs(bounds[0]) > 180 or abs(bounds[2]) > 180:
                st.warning("⚠️ CRS diasumsikan EPSG:3857.")
                shp = shp.set_crs("EPSG:3857")
            else:
                st.warning("⚠️ CRS diasumsikan EPSG:4326.")
                shp = shp.set_crs("EPSG:4326")
        if shp.crs.to_epsg() != 4326:
            shp = shp.to_crs("EPSG:4326")
        if "OBJECTID" not in shp.columns:
            shp.insert(0, "OBJECTID", range(1, len(shp) + 1))
        return shp

def center_map(gdf: gpd.GeoDataFrame):
    try:
        c = gdf.geometry.unary_union.centroid
        return [c.y, c.x], 15
    except Exception:
        return [-6.99, 107.55], 13

# ─── LOGIN ───────────────────────────────────────────────────
def admin_login_form():
    st.markdown('<div class="admin-box">🔐 <b>Area Admin Terproteksi</b><br>Masukkan password untuk membuka dashboard.</div>', unsafe_allow_html=True)
    with st.form("login_admin"):
        pwd = st.text_input("Password Admin", type="password")
        if st.form_submit_button("Masuk"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Password salah.")

def admin_logout_button():
    if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()

# ─── WARNA NAMOBJ ────────────────────────────────────────────
def generate_namobj_colors(gdf_rtrw: gpd.GeoDataFrame) -> dict:
    """Generate warna unik per NAMOBJ secara otomatis."""
    import hashlib
    colors = {}
    if "NAMOBJ" not in gdf_rtrw.columns:
        return colors
    unique_names = gdf_rtrw["NAMOBJ"].dropna().unique().tolist()
    for name in unique_names:
        h = hashlib.md5(str(name).encode()).hexdigest()
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        r = max(60, min(220, r))
        g = max(60, min(220, g))
        b = max(60, min(220, b))
        colors[name] = f"#{r:02x}{g:02x}{b:02x}"
    return colors

# ─── SIDEBAR ─────────────────────────────────────────────────
def render_sidebar(gdf: gpd.GeoDataFrame):
    st.sidebar.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">🗺️ WebGIS Tata Ruang</div>
        <div class="sidebar-brand-subtitle">Dashboard interaktif pengelolaan & publikasi data rekomendasi teknis pemanfaatan ruang.</div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("### MENU UTAMA")
    page = st.sidebar.radio(
        "Navigasi",
        ["🏠  Beranda", "🗺️  Peta Publik", "🔐  Admin"],
        label_visibility="collapsed",
    )

    total    = len(gdf)
    n_pmnft  = gdf["PEMANFAATAN RUANG"].nunique() if "PEMANFAATAN RUANG" in gdf.columns else 0
    n_zonasi = gdf["PERATURAN ZONASI"].nunique()  if "PERATURAN ZONASI" in gdf.columns else 0
    n_tahun  = gdf["TAHUN"].nunique()             if "TAHUN"           in gdf.columns else 0

    # Ringkasan NAMOBJ dari RTRW
    namobj_rows = ""
    if RTRW_FILE.exists():
        try:
            _rtrw_tmp = gpd.read_file(str(RTRW_FILE))
            if "NAMOBJ" in _rtrw_tmp.columns:
                namobj_counts = _rtrw_tmp["NAMOBJ"].value_counts()
                namobj_colors = generate_namobj_colors(_rtrw_tmp)
                for nm, cnt in namobj_counts.items():
                    col_hex = namobj_colors.get(nm, "#9b59b6")
                    namobj_rows += (
                        f'<div class="sidebar-stat" style="display:flex;align-items:center;gap:6px;margin-bottom:5px;">'
                        f'<span style="display:inline-block;width:10px;height:10px;border-radius:3px;'
                        f'background:{col_hex};flex-shrink:0;"></span>'
                        f'<span style="font-size:0.78rem;color:#5f6f83;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
                        f'{nm}</span>'
                        f'<b style="color:#9b59b6;font-size:0.78rem;">{cnt}</b>'
                        f'</div>'
                    )
        except Exception:
            namobj_rows = ""

    rtrw_summary = f"""
    <div class="sidebar-mini-card" style="margin-top:14px;">
        <div class="sidebar-mini-title">🟣 Zona RTRW (NAMOBJ)</div>
        {namobj_rows if namobj_rows else '<div class="sidebar-note">Data RTRW belum tersedia.</div>'}
    </div>""" if RTRW_FILE.exists() else ""

    st.sidebar.markdown(f"""
    <div class="sidebar-mini-card">
        <div class="sidebar-mini-title">📊 Ringkasan Data</div>
        <div class="sidebar-stat">Total data : <b style="color:#4c7aaa">{total}</b></div>
        <div class="sidebar-stat">Jenis pemanfaatan : <b style="color:#4c7aaa">{n_pmnft}</b></div>
        <div class="sidebar-stat">Peraturan zonasi : <b style="color:#4c7aaa">{n_zonasi}</b></div>
        <div class="sidebar-stat" style="margin-bottom:0">Tahun : <b style="color:#4c7aaa">{n_tahun}</b></div>
    </div>
    {rtrw_summary}
    <div class="sidebar-mini-card">
        <div class="sidebar-mini-title">🗂️ Layer Peta</div>
        <div class="sidebar-note">
            <span style="display:inline-block;width:10px;height:3px;border-radius:2px;background:#2d6a4f;margin-right:6px;"></span>Batas Kab. Bandung<br style="margin-bottom:4px;">
            <span style="display:inline-block;width:10px;height:3px;border-radius:2px;background:#e07b39;margin-right:6px;margin-top:5px;"></span>Batas Kec. Katapang<br style="margin-bottom:4px;">
            <span style="display:inline-block;width:10px;height:3px;border-radius:2px;background:#9b59b6;margin-right:6px;margin-top:5px;"></span>RTRW<br style="margin-bottom:4px;">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#4c7aaa;opacity:0.7;margin-right:6px;margin-top:5px;"></span>Pemanfaatan Ruang
        </div>
    </div>
    <div class="sidebar-mini-card">
        <div class="sidebar-mini-title">✨ Catatan</div>
        <div class="sidebar-note">Gunakan <b>Peta Publik</b> untuk melihat data spasial, dan <b>Admin</b> untuk upload SHP atau edit data.</div>
    </div>
    """, unsafe_allow_html=True)
    return page

# ─── INIT ────────────────────────────────────────────────────
if not st.session_state.app_loaded:
    show_loading()
    st.session_state.app_loaded = True

gdf           = load_data()
gdf_kabupaten = load_boundary(str(KABUPATEN_FILE)) if KABUPATEN_FILE.exists() else None
gdf_kecamatan = load_boundary(str(KECAMATAN_FILE)) if KECAMATAN_FILE.exists() else None
gdf_rtrw      = load_boundary(str(RTRW_FILE))      if RTRW_FILE.exists()      else None
page          = render_sidebar(gdf)

def display_cols(df):
    return [c for c in df.columns if c != "geometry"]


# ════════════════════════════════════════════════════════════
# 🏠 BERANDA
# ════════════════════════════════════════════════════════════
if page == "🏠  Beranda":

    st.markdown(f"""
    <div class="hero-box page-enter">
        <div class="hero-scan"></div>
        <div class="mini-label">🌐 Portal Spasial Modern</div>
        <div class="hero-title">{APP_TITLE}</div>
        <div class="hero-subtitle">{APP_SUBTITLE}</div>
    </div>
    """, unsafe_allow_html=True)

    n_pmnft  = gdf["PEMANFAATAN RUANG"].nunique() if "PEMANFAATAN RUANG" in gdf.columns else 0
    n_zonasi = gdf["PERATURAN ZONASI"].nunique()  if "PERATURAN ZONASI" in gdf.columns else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("📍 Total Data",        len(gdf))
    with c2: st.metric("🏙️ Pemanfaatan Ruang", n_pmnft)
    with c3: st.metric("📋 Peraturan Zonasi",  n_zonasi)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("""
        <div class="info-card page-enter page-enter-delay-2">
            <div class="section-title">🏛️ Tentang Platform</div>
            <p style="color:#68798d;font-size:0.86rem;line-height:1.75;margin-bottom:14px;">
                Sistem ini dirancang untuk mendukung pengelolaan
                <b style="color:#4c7aaa">Rekomendasi Teknis Pemanfaatan Ruang</b>
                secara lebih cepat, tertib, dan transparan.
            </p>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(76,122,170,0.12)">🗺️</div>
                <div class="info-item-text"><div class="title">Visualisasi Peta Interaktif</div>
                <div class="desc">Tampilkan polygon pemanfaatan ruang di atas basemap dengan klik-info detail.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(244,190,107,0.16)">📂</div>
                <div class="info-item-text"><div class="title">Upload & Manajemen Data SHP</div>
                <div class="desc">Admin dapat mengunggah shapefile (.zip) untuk memperbarui layer spasial.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(104,121,141,0.14)">🔍</div>
                <div class="info-item-text"><div class="title">Filter & Pencarian Data</div>
                <div class="desc">Filter berdasarkan tahun, jenis pemanfaatan, atau peraturan zonasi.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(155,89,182,0.12)">🏗️</div>
                <div class="info-item-text"><div class="title">Layer RTRW Terintegrasi</div>
                <div class="desc">Overlay data RTRW pada peta untuk analisis kesesuaian pemanfaatan ruang.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(76,122,170,0.12)">🔐</div>
                <div class="info-item-text"><div class="title">Akses Admin Terproteksi</div>
                <div class="desc">Dashboard admin dilindungi password — hanya pengelola yang dapat mengedit data.</div></div>
            </div>
        </div>
        <div class="info-card page-enter page-enter-delay-3">
            <div class="section-title">⚖️ Dasar Hukum</div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(244,190,107,0.18)">📜</div>
                <div class="info-item-text"><div class="title">UU No. 26 Tahun 2007</div>
                <div class="desc">Undang-Undang tentang Penataan Ruang.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(244,190,107,0.18)">📜</div>
                <div class="info-item-text"><div class="title">PP No. 21 Tahun 2021</div>
                <div class="desc">Peraturan Pemerintah tentang Penyelenggaraan Penataan Ruang.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(244,190,107,0.18)">📜</div>
                <div class="info-item-text"><div class="title">Permen ATR/BPN No. 11 Tahun 2021</div>
                <div class="desc">Tata Cara Penyusunan dan Penerbitan Persetujuan Substansi RTRW.</div></div>
            </div>
            <div class="info-item" style="padding-bottom:0">
                <div class="info-item-icon" style="background:rgba(244,190,107,0.18)">📜</div>
                <div class="info-item-text"><div class="title">Perda RTRW Setempat</div>
                <div class="desc">Peraturan Daerah tentang Rencana Tata Ruang Wilayah sebagai acuan lokal.</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("""
        <div class="info-card page-enter page-enter-delay-2">
            <div class="section-title">🏗️ Jenis Pemanfaatan Ruang</div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(76,122,170,0.12)">🏘️</div>
                <div class="info-item-text"><div class="title">Kawasan Permukiman</div>
                <div class="desc">Area peruntukan hunian perkotaan maupun perdesaan.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(104,121,141,0.14)">🛒</div>
                <div class="info-item-text"><div class="title">Kawasan Perdagangan & Jasa</div>
                <div class="desc">Pusat perbelanjaan, ruko, pasar, perkantoran swasta.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(244,190,107,0.16)">🌳</div>
                <div class="info-item-text"><div class="title">Ruang Terbuka Hijau</div>
                <div class="desc">Taman kota, hutan kota, jalur hijau, sempadan sungai.</div></div>
            </div>
            <div class="info-item">
                <div class="info-item-icon" style="background:rgba(76,122,170,0.10)">🏭</div>
                <div class="info-item-text"><div class="title">Kawasan Industri</div>
                <div class="desc">Area industri besar, sedang, maupun rumah tangga.</div></div>
            </div>
            <div class="info-item" style="padding-bottom:0">
                <div class="info-item-icon" style="background:rgba(244,190,107,0.16)">🌾</div>
                <div class="info-item-text"><div class="title">Kawasan Pertanian & Lahan Khusus</div>
                <div class="desc">Lahan pertanian pangan berkelanjutan dan kawasan lindung.</div></div>
            </div>
        </div>
        <div class="info-card page-enter page-enter-delay-3">
            <div class="section-title">📋 Status Kesesuaian RTRW</div>
            <div style="display:flex;flex-direction:column;gap:8px;">
                <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.18);border-radius:10px;">
                    <span style="font-size:1.1rem">✅</span>
                    <div><div style="font-size:0.82rem;font-weight:700;color:#16a34a">Sesuai RTRW</div>
                    <div style="font-size:0.74rem;color:#68798d">Pemanfaatan sesuai rencana tata ruang yang berlaku.</div></div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:rgba(244,190,107,0.14);border:1px solid rgba(244,190,107,0.24);border-radius:10px;">
                    <span style="font-size:1.1rem">⚠️</span>
                    <div><div style="font-size:0.82rem;font-weight:700;color:#a16207">Perlu Verifikasi</div>
                    <div style="font-size:0.74rem;color:#68798d">Memerlukan pengecekan lapangan atau kelengkapan dokumen.</div></div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.18);border-radius:10px;">
                    <span style="font-size:1.1rem">❌</span>
                    <div><div style="font-size:0.82rem;font-weight:700;color:#dc2626">Tidak Sesuai RTRW</div>
                    <div style="font-size:0.74rem;color:#68798d">Terindikasi penyimpangan — perlu penanganan lebih lanjut.</div></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('''<div class="info-card page-enter page-enter-delay-4">
        <div class="section-title">🔄 Alur Rekomendasi Teknis Pemanfaatan Ruang</div>''', unsafe_allow_html=True)

    components.html("""
<!DOCTYPE html>
<html>
<head>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0;font-family:'Plus Jakarta Sans',sans-serif;}
body{background:transparent;}
.wrap{padding:4px 8px 8px 8px;}
.row{display:grid;grid-template-columns:1fr 44px 1fr;align-items:center;min-height:80px;}
.card-l{text-align:right;padding-right:12px;}
.card-r{text-align:left;padding-left:12px;}
.empty{visibility:hidden;}
.card{display:inline-block;padding:10px 14px;border-radius:12px;max-width:260px;text-align:left;}
.num{font-size:0.6rem;font-weight:800;letter-spacing:0.8px;text-transform:uppercase;margin-bottom:2px;opacity:0.75;}
.ttl{font-size:0.82rem;font-weight:700;line-height:1.35;margin-bottom:3px;}
.dsc{font-size:0.7rem;color:#68798d;line-height:1.45;}
.spine{display:flex;flex-direction:column;align-items:center;}
.circle{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.82rem;font-weight:800;color:#fff;flex-shrink:0;box-shadow:0 4px 12px rgba(0,0,0,0.13);}
.line{width:2px;flex:1;min-height:14px;background:linear-gradient(to bottom,rgba(76,122,170,0.22),rgba(76,122,170,0.06));}
.line-t{background:transparent!important;}
@media(max-width:500px){
  .row{grid-template-columns:30px 1fr;}
  .card-l{display:none;}
  .card-r{display:block!important;visibility:visible!important;padding-left:8px;}
  .empty{display:none;}
  .circle{width:26px;height:26px;font-size:0.68rem;}
  .card{max-width:100%;}
  .ttl{font-size:0.76rem;}
  .dsc{font-size:0.66rem;}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="row">
    <div class="card-l">
      <div class="card" style="background:rgba(76,122,170,0.09);border:1px solid rgba(76,122,170,0.22);">
        <div class="num" style="color:#4c7aaa">Langkah 1</div>
        <div class="ttl" style="color:#4c7aaa">Pelaku Usaha Membuat NIB melalui OSS</div>
        <div class="dsc">Pemohon mendaftarkan Nomor Induk Berusaha melalui portal oss.go.id</div>
      </div>
    </div>
    <div class="spine">
      <div class="line line-t" style="min-height:6px;"></div>
      <div class="circle" style="background:#4c7aaa;">1</div>
      <div class="line"></div>
    </div>
    <div class="card-r empty"><div class="card"></div></div>
  </div>
  <div class="row">
    <div class="card-l empty"><div class="card"></div></div>
    <div class="spine">
      <div class="circle" style="background:#e07b39;">2</div>
      <div class="line"></div>
    </div>
    <div class="card-r">
      <div class="card" style="background:rgba(224,123,57,0.09);border:1px solid rgba(224,123,57,0.22);">
        <div class="num" style="color:#c05e1a">Langkah 2</div>
        <div class="ttl" style="color:#c05e1a">Pendaftaran &amp; Melengkapi Dokumen</div>
        <div class="dsc">Pemohon mendaftar dan melengkapi seluruh dokumen yang dipersyaratkan</div>
      </div>
    </div>
  </div>
  <div class="row">
    <div class="card-l">
      <div class="card" style="background:rgba(122,111,160,0.09);border:1px solid rgba(122,111,160,0.22);">
        <div class="num" style="color:#5b5085">Langkah 3</div>
        <div class="ttl" style="color:#5b5085">Diproses Sekretariat &amp; Disposisi Kepala Dinas</div>
        <div class="dsc">Berkas masuk ke sekretariat, kemudian didisposisikan kepada Kepala Dinas</div>
      </div>
    </div>
    <div class="spine">
      <div class="circle" style="background:#7a6fa0;">3</div>
      <div class="line"></div>
    </div>
    <div class="card-r empty"><div class="card"></div></div>
  </div>
  <div class="row">
    <div class="card-l empty"><div class="card"></div></div>
    <div class="spine">
      <div class="circle" style="background:#5a8f7b;">4</div>
      <div class="line"></div>
    </div>
    <div class="card-r">
      <div class="card" style="background:rgba(90,143,123,0.09);border:1px solid rgba(90,143,123,0.22);">
        <div class="num" style="color:#3a6e5c">Langkah 4</div>
        <div class="ttl" style="color:#3a6e5c">Disposisi Bidang Tata Ruang</div>
        <div class="dsc">Kepala Dinas mendisposisikan berkas ke Bidang Tata Ruang untuk ditindaklanjuti</div>
      </div>
    </div>
  </div>
  <div class="row">
    <div class="card-l">
      <div class="card" style="background:rgba(192,133,74,0.09);border:1px solid rgba(192,133,74,0.22);">
        <div class="num" style="color:#8a5c1c">Langkah 5</div>
        <div class="ttl" style="color:#8a5c1c">Survei / Verifikasi Berkas</div>
        <div class="dsc">Survei lapangan jika luas &gt; 1000 m&#178; &mdash; Verifikasi berkas jika luas &le; 1000 m&#178;</div>
      </div>
    </div>
    <div class="spine">
      <div class="circle" style="background:#c0854a;">5</div>
      <div class="line"></div>
    </div>
    <div class="card-r empty"><div class="card"></div></div>
  </div>
  <div class="row">
    <div class="card-l empty"><div class="card"></div></div>
    <div class="spine">
      <div class="circle" style="background:#4c7aaa;">6</div>
      <div class="line"></div>
    </div>
    <div class="card-r">
      <div class="card" style="background:rgba(76,122,170,0.09);border:1px solid rgba(76,122,170,0.20);">
        <div class="num" style="color:#4c7aaa">Langkah 6</div>
        <div class="ttl" style="color:#4c7aaa">Pengolahan Berkas</div>
        <div class="dsc">Berkas diproses dan diolah oleh staf teknis Bidang Tata Ruang</div>
      </div>
    </div>
  </div>
  <div class="row">
    <div class="card-l">
      <div class="card" style="background:rgba(122,111,160,0.09);border:1px solid rgba(122,111,160,0.22);">
        <div class="num" style="color:#5b5085">Langkah 7</div>
        <div class="ttl" style="color:#5b5085">Proses Revisi &amp; Persetujuan</div>
        <div class="dsc">Draft rekomendasi direvisi dan dimintakan persetujuan internal</div>
      </div>
    </div>
    <div class="spine">
      <div class="circle" style="background:#7a6fa0;">7</div>
      <div class="line"></div>
    </div>
    <div class="card-r empty"><div class="card"></div></div>
  </div>
  <div class="row">
    <div class="card-l empty"><div class="card"></div></div>
    <div class="spine">
      <div class="circle" style="background:#5a8f7b;">8</div>
      <div class="line"></div>
    </div>
    <div class="card-r">
      <div class="card" style="background:rgba(90,143,123,0.09);border:1px solid rgba(90,143,123,0.22);">
        <div class="num" style="color:#3a6e5c">Langkah 8</div>
        <div class="ttl" style="color:#3a6e5c">Verifikasi oleh Kepala Bidang</div>
        <div class="dsc">Kepala Bidang Tata Ruang memverifikasi dan menyetujui draft rekomendasi</div>
      </div>
    </div>
  </div>
  <div class="row">
    <div class="card-l">
      <div class="card" style="background:rgba(104,121,141,0.09);border:1px solid rgba(104,121,141,0.22);">
        <div class="num" style="color:#4a5568">Langkah 9</div>
        <div class="ttl" style="color:#4a5568">Proses TTD Kepala Bidang / Kepala Dinas</div>
        <div class="dsc">Surat ditandatangani oleh Kepala Bidang atau Kepala Dinas sesuai kewenangan</div>
      </div>
    </div>
    <div class="spine">
      <div class="circle" style="background:#68798d;">9</div>
      <div class="line"></div>
    </div>
    <div class="card-r empty"><div class="card"></div></div>
  </div>
  <div class="row">
    <div class="card-l empty"><div class="card"></div></div>
    <div class="spine">
      <div class="circle" style="background:#4c7aaa;">10</div>
      <div class="line"></div>
    </div>
    <div class="card-r">
      <div class="card" style="background:rgba(76,122,170,0.09);border:1px solid rgba(76,122,170,0.20);">
        <div class="num" style="color:#4c7aaa">Langkah 10</div>
        <div class="ttl" style="color:#4c7aaa">Penomoran Surat</div>
        <div class="dsc">Surat rekomendasi teknis diberi nomor registrasi resmi dari sekretariat</div>
      </div>
    </div>
  </div>
  <div class="row">
    <div class="card-l">
      <div class="card" style="background:rgba(45,106,79,0.09);border:1px solid rgba(45,106,79,0.22);">
        <div class="num" style="color:#2d6a4f">Langkah 11</div>
        <div class="ttl" style="color:#2d6a4f">Pengambilan Produk</div>
        <div class="dsc">Pemohon mengambil surat Rekomendasi Teknis yang telah selesai diterbitkan</div>
      </div>
    </div>
    <div class="spine">
      <div class="circle" style="background:#2d6a4f;">11</div>
      <div class="line line-t"></div>
    </div>
    <div class="card-r empty"><div class="card"></div></div>
  </div>
</div>
</body>
</html>
""", height=1400, scrolling=False)

    st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# 🗺️ PETA PUBLIK
# ════════════════════════════════════════════════════════════
elif page == "🗺️  Peta Publik":

    st.markdown("""
    <div class="hero-box page-enter">
        <div class="hero-scan"></div>
        <div class="mini-label">🌐 Informasi Publik</div>
        <div class="hero-title">Peta Publik Pemanfaatan Ruang</div>
        <div class="hero-subtitle">Lihat data spasial, lakukan filter, dan telusuri detail wilayah secara interaktif.</div>
    </div>
    """, unsafe_allow_html=True)

    show_rtrw = st.checkbox(
        "🟣 Tampilkan Layer RTRW",
        value=True,
        help="Centang untuk menampilkan/menyembunyikan layer RTRW pada peta",
        disabled=(gdf_rtrw is None),
    )
    if gdf_rtrw is None:
        st.caption("⚠️ File RTRW.geojson tidak ditemukan di direktori aplikasi.")

    tahun_opts = ["Semua"] + sorted(gdf["TAHUN"].dropna().astype(str).unique().tolist()) \
                 if "TAHUN" in gdf.columns else ["Semua"]
    pmnft_opts = ["Semua"] + sorted(gdf["PEMANFAATAN RUANG"].dropna().astype(str).unique().tolist()) \
                 if "PEMANFAATAN RUANG" in gdf.columns else ["Semua"]
    zona_opts  = ["Semua"] + sorted(gdf["PERATURAN ZONASI"].dropna().astype(str).unique().tolist()) \
                 if "PERATURAN ZONASI" in gdf.columns else ["Semua"]

    c1, c2 = st.columns(2)
    with c1: f_tahun = st.selectbox("Filter Tahun",       tahun_opts)
    with c2: f_pmnft = st.selectbox("Filter Pemanfaatan", pmnft_opts)

    c3, c4 = st.columns(2)
    with c3: f_zona = st.selectbox("Filter Zonasi",       zona_opts)
    with c4: f_kw   = st.text_input("🔍 Cari REMARK/KBLI")

    fgdf = gdf.copy()
    if f_tahun != "Semua":
        fgdf = fgdf[fgdf["TAHUN"].astype(str) == f_tahun]
    if f_pmnft != "Semua":
        fgdf = fgdf[fgdf["PEMANFAATAN RUANG"].astype(str) == f_pmnft]
    if f_zona != "Semua":
        fgdf = fgdf[fgdf["PERATURAN ZONASI"].astype(str) == f_zona]
    if f_kw:
        mask = pd.Series(False, index=fgdf.index)
        for col in ["REMARK", "KODEKBLI"]:
            if col in fgdf.columns:
                mask |= fgdf[col].astype(str).str.contains(f_kw, case=False, na=False)
        fgdf = fgdf[mask]

    st.caption(f"Menampilkan **{len(fgdf)}** dari **{len(gdf)}** data")

    with st.spinner("⏳ Memuat peta…"):
        center, zoom = center_map(fgdf if not fgdf.empty else gdf)
        m = leafmap.Map(center=center, zoom=zoom)
        m.add_basemap("OpenStreetMap")

        if gdf_kabupaten is not None:
            m.add_gdf(gdf_kabupaten, layer_name="Batas Kab. Bandung",
                style={"color":"#2d6a4f","fillColor":"#2d6a4f","fillOpacity":0.04,"weight":2.0,"dashArray":"8 5"},
                info_mode="on_hover")

        if gdf_kecamatan is not None:
            m.add_gdf(gdf_kecamatan, layer_name="Batas Kec. Katapang",
                style={"color":"#e07b39","fillColor":"#e07b39","fillOpacity":0.06,"weight":2.5,"dashArray":"5 4"},
                info_mode="on_hover")

        if gdf_rtrw is not None and show_rtrw:
            if "NAMOBJ" in gdf_rtrw.columns:
                _namobj_colors = generate_namobj_colors(gdf_rtrw)
                for nm, grp in gdf_rtrw.groupby("NAMOBJ"):
                    col = _namobj_colors.get(nm, "#9b59b6")
                    m.add_gdf(
                        grp.reset_index(drop=True),
                        layer_name=f"RTRW — {nm}",
                        style={"color": col, "fillColor": col, "fillOpacity": 0.25, "weight": 1.5, "dashArray": "5 3"},
                        info_mode="on_hover",
                    )
            else:
                m.add_gdf(gdf_rtrw, layer_name="RTRW",
                    style={"color":"#9b59b6","fillColor":"#9b59b6","fillOpacity":0.15,"weight":2.0,"dashArray":"6 4"},
                    info_mode="on_hover")

        if not fgdf.empty:
            m.add_gdf(fgdf, layer_name="Pemanfaatan Ruang",
                style={"color":"#4c7aaa","fillColor":"#4c7aaa","fillOpacity":0.35,"weight":1.5},
                info_mode="on_click")

    m.to_streamlit(height=460)

    if gdf_rtrw is not None and show_rtrw:
        if "NAMOBJ" in gdf_rtrw.columns:
            _namobj_colors = generate_namobj_colors(gdf_rtrw)
            n_namobj = gdf_rtrw["NAMOBJ"].nunique()
            dots = "".join([
                f'<span style="display:inline-block;width:10px;height:10px;border-radius:3px;'
                f'background:{_namobj_colors.get(nm,"#9b59b6")};margin-right:4px;margin-bottom:2px;'
                f'title="{nm}"></span>'
                for nm in gdf_rtrw["NAMOBJ"].dropna().unique()
            ])
            st.markdown(
                f'<div class="admin-box" style="border-left-color:#9b59b6;color:#6c3483;">'
                f'🟣 <b>Layer RTRW aktif</b> — {len(gdf_rtrw)} polygon | {n_namobj} NAMOBJ unik<br>'
                f'<div style="margin-top:6px;">{dots}</div>'
                f'Hover pada peta untuk melihat atribut.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="admin-box" style="border-left-color:#9b59b6;color:#6c3483;">'
                f'🟣 <b>Layer RTRW aktif</b> — {len(gdf_rtrw)} polygon. Hover pada peta untuk melihat atribut.</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Tabel Data Pemanfaatan Ruang</div>', unsafe_allow_html=True)
    if fgdf.empty:
        st.warning("Tidak ada data yang sesuai filter.")
    else:
        st.dataframe(fgdf[display_cols(fgdf)], use_container_width=True, height=300)
    st.markdown('</div>', unsafe_allow_html=True)

    if gdf_rtrw is not None and show_rtrw:
        with st.expander("📋 Lihat Tabel Data RTRW"):
            st.dataframe(gdf_rtrw[display_cols(gdf_rtrw)], use_container_width=True, height=260)


# ════════════════════════════════════════════════════════════
# 🔐 DASHBOARD ADMIN
# ════════════════════════════════════════════════════════════
elif page == "🔐  Admin":

    st.markdown("""
    <div class="hero-box page-enter">
        <div class="hero-scan"></div>
        <div class="mini-label">🔒 Akses Internal</div>
        <div class="hero-title">Dashboard Admin</div>
        <div class="hero-subtitle">Hanya admin dengan password yang dapat mengunggah dan memperbarui data.</div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.admin_logged_in:
        admin_login_form()
        st.markdown('<div class="upload-note">📌 Password tersimpan aman di <b>Streamlit Secrets</b>.</div>', unsafe_allow_html=True)

    else:
        ca, cb = st.columns([4, 1])
        with ca: st.success("✅ Login sebagai admin.")
        with cb: admin_logout_button()

        tab1, tab2, tab3 = st.tabs(["📤 Upload SHP", "✏️ Edit", "🗑️ Hapus"])

        # ── Tab 1: Upload SHP ────────────────────────────────
        with tab1:
            st.subheader("Upload Data SHP Pemanfaatan Ruang")
            st.markdown('<div class="upload-note">Upload file <b>ZIP</b> berisi .shp + .shx + .dbf + .prj. Data akan otomatis tersimpan ke <b>Google Drive</b>.</div>', unsafe_allow_html=True)
            uploaded_zip = st.file_uploader("Upload SHP dalam ZIP", type=["zip"])
            replace_all  = st.checkbox("Ganti seluruh data lama", value=True)

            if uploaded_zip:
                try:
                    with st.spinner("Membaca shapefile…"):
                        shp_gdf = read_shp_from_zip(uploaded_zip)
                    st.write("Preview (10 baris pertama):")
                    st.dataframe(shp_gdf[display_cols(shp_gdf)].head(10), use_container_width=True)

                    if st.button("💾 Simpan ke Sistem"):
                        with st.spinner("Menyimpan dan mengupload ke Google Drive…"):
                            if replace_all:
                                save_data(shp_gdf)
                            else:
                                combined = gpd.GeoDataFrame(
                                    pd.concat([gdf, shp_gdf], ignore_index=True), crs="EPSG:4326"
                                )
                                combined["OBJECTID"] = range(1, len(combined) + 1)
                                save_data(combined)
                        st.success("✅ Data SHP berhasil disimpan ke Google Drive.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Gagal membaca SHP: {e}")

        # ── Tab 2: Edit Manual ───────────────────────────────
        with tab2:
            st.subheader("Edit Data Manual")
            if gdf.empty:
                st.warning("Belum ada data.")
            else:
                label_col = next((c for c in ["REMARK", "PEMANFAATAN RUANG", "KODEKBLI"] if c in gdf.columns), None)
                id_list   = gdf["OBJECTID"].tolist()

                sel_id = st.selectbox(
                    "Pilih OBJECTID", id_list,
                    format_func=lambda x: (
                        f"ID {x} — {gdf.loc[gdf['OBJECTID']==x, label_col].values[0]}"
                        if label_col else f"ID {x}"
                    ),
                )
                row       = gdf[gdf["OBJECTID"] == sel_id].iloc[0]
                edit_cols = [c for c in gdf.columns if c not in ("OBJECTID", "geometry")]

                with st.form("form_edit"):
                    edited = {}
                    pairs  = [edit_cols[i:i+2] for i in range(0, len(edit_cols), 2)]
                    for pair in pairs:
                        cols_ui = st.columns(len(pair))
                        for ci, col_name in enumerate(pair):
                            with cols_ui[ci]:
                                edited[col_name] = st.text_input(col_name, value=str(row.get(col_name, "")))

                    if st.form_submit_button("🔄 Update Data"):
                        for col_name, val in edited.items():
                            gdf.loc[gdf["OBJECTID"] == sel_id, col_name] = val
                        with st.spinner("Menyimpan ke Google Drive…"):
                            save_data(gdf)
                        st.success("✅ Data berhasil diperbarui.")
                        st.rerun()

        # ── Tab 3: Hapus Data ────────────────────────────────
        with tab3:
            st.subheader("Hapus Data")
            if gdf.empty:
                st.warning("Belum ada data.")
            else:
                label_col = next((c for c in ["REMARK", "PEMANFAATAN RUANG", "KODEKBLI"] if c in gdf.columns), None)
                del_id = st.selectbox(
                    "Pilih ID yang akan dihapus", gdf["OBJECTID"].tolist(),
                    format_func=lambda x: (
                        f"ID {x} — {gdf.loc[gdf['OBJECTID']==x, label_col].values[0]}"
                        if label_col else f"ID {x}"
                    ),
                    key="hapus_id",
                )
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);
                border-left:4px solid #ef4444;border-radius:10px;padding:12px 16px;
                font-size:13px;color:#dc2626;margin:10px 0;">
                ⚠️ Data <b>OBJECTID {del_id}</b> akan dihapus permanen dan tidak bisa dikembalikan.
                </div>""", unsafe_allow_html=True)

                if st.button("🗑️ Hapus Permanen"):
                    with st.spinner("Menghapus dan mengupload ke Google Drive…"):
                        save_data(gdf[gdf["OBJECTID"] != del_id].copy())
                    st.success("✅ Data berhasil dihapus.")
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 Semua Data Pemanfaatan Ruang")
        st.dataframe(gdf[display_cols(gdf)], use_container_width=True, height=350)

# ─── FOOTER ──────────────────────────────────────────────────
st.markdown("---")
st.caption("© WebGIS Rekomendasi Teknis Pemanfaatan Ruang · Tugas Akhir")