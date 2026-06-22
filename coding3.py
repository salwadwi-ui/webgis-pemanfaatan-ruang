"""
🗺️ WebGIS Pemanfaatan Ruang - IMPROVED VERSION (v3)
✅ Sistem Data yang Sama Seperti Script 2 — Lebih Rapi & Efficient
✅ FOLDER ID SUDAH DIPERBAIKI
"""

import os
import io
import time
import base64
import zipfile
import tempfile
import pathlib
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import leafmap.foliumap as leafmap
import folium

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account
from PIL import Image

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚙️ GOOGLE DRIVE SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "1dTdLnvUyRgFDKCSLLKH83ZOb2fou0Mci"  # ✅ Folder ID yang sudah dikonfigurasi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📁 FILE PATHS — Using TEMP_DIR like Script 2
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEMP_DIR = pathlib.Path(tempfile.gettempdir()) / "webgis_cache"
TEMP_DIR.mkdir(exist_ok=True)

# ✅ FILE MAP — Organized like Script 2
FILE_MAP = {
    "DATA PEMANFAATAN.geojson": TEMP_DIR / "DATA PEMANFAATAN.geojson",
    "Batas Administrasi Kabupaten Bandung.geojson": TEMP_DIR / "Batas Administrasi Kabupaten Bandung.geojson",
    "Batas Administrasi Kecamatan Katapang.geojson": TEMP_DIR / "Batas Administrasi Kecamatan Katapang.geojson",
    "RTRW.geojson": TEMP_DIR / "RTRW.geojson",
}

# Quick access paths
DATA_FILE = FILE_MAP["DATA PEMANFAATAN.geojson"]
KABUPATEN_FILE = FILE_MAP["Batas Administrasi Kabupaten Bandung.geojson"]
KECAMATAN_FILE = FILE_MAP["Batas Administrasi Kecamatan Katapang.geojson"]
RTRW_FILE = FILE_MAP["RTRW.geojson"]

# 🖼️ LOGO
LOGO_PATH = r"logoupimerah.png"

# 🔐 ADMIN PASSWORD
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📱 PAGE CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.set_page_config(
    page_title="WebGIS Pemanfaatan Ruang",
    page_icon="🗺️",
    layout="wide"
)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

[data-testid="stToolbar"] {
    display: none !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stStatusWidget"] {
    display: none !important;
}

[data-testid="stHeader"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 CSS STYLING (sama seperti script original)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --navy: #1a3a52;
    --gold: #FFD700;
    --teal: #00BCD4;
    --coral: #FF6B6B;
}

* { box-sizing: border-box; }
html, body { 
    font-family: 'Inter', sans-serif !important;
    background: linear-gradient(135deg, #f5f7fa 0%, #eef2f7 100%) !important;
}

.stApp { background: linear-gradient(135deg, #f5f7fa 0%, #eef2f7 100%) !important; }

.header-gold-bar {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafb 100%);
    padding: 16px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 85px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    position: sticky;
    top: 0;
    z-index: 999;
    width: 100%;
    border-bottom: 3px solid;
    border-image: linear-gradient(90deg, #FFD700, #00BCD4) 1;
}

.header-left { display: flex; align-items: center; gap: 16px; }
.header-logo-img { max-width: 65px; height: auto; max-height: 65px; object-fit: contain; }
.header-logo-placeholder {
    width: 58px; height: 58px;
    background: linear-gradient(135deg, #FFD700, #00BCD4);
    border-radius: 12px; display: flex; align-items: center; justify-content: center;
    font-size: 30px; font-weight: bold; color: white;
}

.stButton > button {
    background: linear-gradient(135deg, #1a3a52, #2a5a72) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    padding: 12px 24px !important; font-weight: 700 !important; font-size: 11px !important;
    text-transform: uppercase !important; letter-spacing: 1px !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #FFD700, #FFC700) !important;
    color: #1a3a52 !important; transform: translateY(-3px) !important;
    box-shadow: 0 8px 20px rgba(255, 215, 0, 0.3) !important;
}

.hero-section {
    background: linear-gradient(135deg, #1a3a52 0%, #2a5a72 100%);
    color: white; padding: 60px 40px; text-align: center;
    border-radius: 12px; margin-bottom: 30px;
}
.hero-title { font-family: 'Playfair Display', serif; font-size: 2.5rem; font-weight: 800; margin: 0; text-transform: uppercase; }
.hero-subtitle { font-size: 1rem; opacity: 0.9; margin-top: 12px; color: #00BCD4; }

.feature-box {
    background: white; border-radius: 12px; padding: 24px; text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1.5px solid #e8ecf1;
    transition: all 0.3s ease;
}
.feature-box:hover { transform: translateY(-8px); box-shadow: 0 12px 24px rgba(26, 58, 82, 0.12); border-color: #FFD700; }
.feature-icon { font-size: 2.5rem; margin-bottom: 12px; }
.feature-title { font-size: 1.1rem; font-weight: 700; color: #1a3a52; margin-bottom: 8px; text-transform: uppercase; }
.feature-desc { font-size: 0.85rem; color: #666; line-height: 1.5; }

.stat-box {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafb 100%);
    color: #1a3a52; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #e8ecf1;
}
.stat-number {
    font-family: 'Playfair Display', serif; font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(135deg, #FFD700, #00BCD4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0;
}
.stat-label { font-size: 0.75rem; color: #666; text-transform: uppercase; font-weight: 600; margin-top: 8px; }

.filter-label {
    font-size: 10px !important; font-weight: 700 !important; color: #1a3a52 !important;
    text-transform: uppercase !important; letter-spacing: 1px !important; margin-bottom: 8px !important;
}

.stSelectbox > div > div {
    background: white !important; border: 2px solid #e8ecf1 !important; border-radius: 10px !important;
}
.stSelectbox * { color: #1a3a52 !important; font-weight: 500 !important; }

div[data-baseweb="select"] > div {
    background: white !important; border: 2px solid #e8ecf1 !important;
}
div[data-baseweb="select"] [role="option"] {
    background: white !important; color: #1a3a52 !important;
}

.footer {
    background: linear-gradient(135deg, #1a3a52 0%, #2a5a72 100%);
    color: white; padding: 40px; border-radius: 12px; margin-top: 50px; text-align: center; font-size: 0.85rem;
}

.drive-status {
    background: rgba(76, 175, 80, 0.1); border: 1px solid rgba(76, 175, 80, 0.3);
    border-left: 4px solid #4CAF50; border-radius: 8px; padding: 12px;
    margin: 10px 0; font-size: 13px; color: #2e7d32;
}

.drive-status.loading {
    background: rgba(33, 150, 243, 0.1); border: 1px solid rgba(33, 150, 243, 0.3);
    border-left: 4px solid #2196F3; color: #1565c0;
}

@media (max-width: 768px) {
    .hero-title { font-size: 1.8rem; }
    .header-gold-bar { flex-direction: column; gap: 12px; }
}
</style>

<script>
function fixSelectboxColors() {
    const selects = document.querySelectorAll('[data-baseweb="select"]');
    selects.forEach((select) => {
        const allText = select.querySelectorAll('*');
        allText.forEach((el) => {
            if (el.textContent && el.textContent.trim()) {
                el.style.color = '#1a3a52';
            }
        });
    });
}

document.addEventListener('DOMContentLoaded', fixSelectboxColors);
setInterval(fixSelectboxColors, 500);
</script>
""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📦 SESSION STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "landing"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🖼️ LOGO LOADING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@st.cache_data
def load_logo_base64(logo_path):
    try:
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_data = img_file.read()
                b64_string = base64.b64encode(img_data).decode()
                return b64_string, True
        return None, False
    except:
        return None, False

logo_base64, logo_exists = load_logo_base64(LOGO_PATH)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ☁️ GOOGLE DRIVE FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@st.cache_resource
def get_drive_service():
    """Get Google Drive service dengan error handling"""
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        return None

def get_file_id(service, filename: str):
    """Cari file di folder Drive berdasarkan nama"""
    try:
        if not service or not FOLDER_ID:
            return None
        results = service.files().list(
            q=f"name='{filename}' and '{FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None
    except:
        return None

def download_from_drive(service, filename: str, dest_path: pathlib.Path) -> bool:
    """Download file dari Drive ke lokal"""
    try:
        if not service:
            return False
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
    except Exception as e:
        return False

def upload_to_drive(service, local_path: pathlib.Path, filename: str):
    """Upload atau update file ke Google Drive"""
    try:
        if not service:
            return False
        file_id = get_file_id(service, filename)
        media = MediaFileUpload(str(local_path), mimetype="application/geo+json", resumable=True)
        if file_id:
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            metadata = {"name": filename, "parents": [FOLDER_ID]}
            service.files().create(body=metadata, media_body=media).execute()
        return True
    except Exception as e:
        st.error(f"❌ Gagal upload ke Drive: {str(e)}")
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📂 DATA LOADING FUNCTIONS — Simplified like Script 2
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@st.cache_data(ttl=0)  # ✅ Changed: ttl=0 like Script 2 (no caching)
def load_data():
    """Load main data from file"""
    try:
        if not DATA_FILE.exists():
            return gpd.GeoDataFrame()
        
        gdf = gpd.read_file(str(DATA_FILE))
        
        if gdf.empty:
            return gpd.GeoDataFrame()
        
        # Normalize CRS
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        
        # Add OBJECTID
        if "OBJECTID" not in gdf.columns:
            gdf.insert(0, "OBJECTID", range(1, len(gdf) + 1))
        
        return gdf
    except Exception as e:
        st.warning(f"Error loading data: {str(e)}")
        return gpd.GeoDataFrame()

@st.cache_data(ttl=0)  # ✅ Changed: ttl=0 like Script 2
def load_boundary(filepath: str) -> gpd.GeoDataFrame:
    """Load boundary/reference data"""
    try:
        if not pathlib.Path(filepath).exists():
            return gpd.GeoDataFrame()
        
        gdf = gpd.read_file(filepath)
        
        if gdf.empty:
            return gpd.GeoDataFrame()
        
        # Normalize CRS
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        
        return gdf
    except Exception as e:
        st.warning(f"Error loading boundary: {str(e)}")
        return gpd.GeoDataFrame()

def save_data(gdf: gpd.GeoDataFrame):
    """Save data to local + upload to Google Drive"""
    try:
        # Normalize CRS
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        
        # Save to local file
        gdf.to_file(str(DATA_FILE), driver="GeoJSON")
        st.success("✅ Data tersimpan ke file lokal!")
        
        # Upload to Drive
        drive_service = get_drive_service()
        if drive_service:
            with st.spinner("⏳ Uploading ke Google Drive..."):
                if upload_to_drive(drive_service, DATA_FILE, "DATA PEMANFAATAN.geojson"):
                    st.success("✅ Data juga tersimpan ke Google Drive!")
        
        # Clear cache
        st.cache_data.clear()
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def read_shp_from_zip(uploaded_file) -> gpd.GeoDataFrame:
    """Support SHP, KML, KMZ"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = os.path.join(tmpdir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            
            if uploaded_file.name.endswith('.zip'):
                with zipfile.ZipFile(temp_path, "r") as z:
                    z.extractall(tmpdir)
                shp_files = list(Path(tmpdir).rglob("*.shp"))
                if shp_files:
                    gdf = gpd.read_file(str(shp_files[0]))
                else:
                    raise ValueError("Tidak ada .shp di ZIP")
            
            elif uploaded_file.name.endswith('.kml'):
                gdf = gpd.read_file(temp_path, driver='KML')
            
            elif uploaded_file.name.endswith('.kmz'):
                with zipfile.ZipFile(temp_path, "r") as z:
                    z.extractall(tmpdir)
                kml_files = list(Path(tmpdir).rglob("*.kml"))
                if kml_files:
                    gdf = gpd.read_file(str(kml_files[0]), driver='KML')
                else:
                    raise ValueError("Tidak ada .kml di KMZ")
            else:
                raise ValueError(f"Format {uploaded_file.name} tidak didukung")
            
            # Normalize CRS
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")
            elif gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs("EPSG:4326")
            
            # Add OBJECTID
            if "OBJECTID" not in gdf.columns:
                gdf.insert(0, "OBJECTID", range(1, len(gdf) + 1))
            
            return gdf
    except Exception as e:
        st.error(f"Error membaca file: {str(e)}")
        raise

def center_map(gdf: gpd.GeoDataFrame):
    """Calculate map center"""
    try:
        if gdf.empty:
            return [-6.99, 107.55], 13
        c = gdf.geometry.unary_union.centroid
        return [c.y, c.x], 13
    except:
        return [-6.99, 107.55], 13

def display_cols(df):
    """Get columns to display (exclude geometry)"""
    return [c for c in df.columns if c != "geometry"]

def generate_namobj_colors(gdf_rtrw: gpd.GeoDataFrame) -> dict:
    """Generate warna unik per NAMOBJ"""
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 INITIALIZE DATA — Download from Drive + Load
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with st.spinner("⏳ Loading data dari Google Drive..."):
    drive_service = get_drive_service()
    
    # ✅ Download files from Drive if they don't exist locally
    if drive_service:
        for drive_filename, local_path in FILE_MAP.items():
            if not local_path.exists():
                download_from_drive(drive_service, drive_filename, local_path)
    
    # Load all data
    gdf = load_data()
    gdf_kabupaten = load_boundary(str(KABUPATEN_FILE))
    gdf_kecamatan = load_boundary(str(KECAMATAN_FILE))
    gdf_rtrw = load_boundary(str(RTRW_FILE))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎨 HEADER & NAVIGATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

header_html = f"""
<div class="header-gold-bar">
    <div class="header-left">
        {"<img src=\"data:image/png;base64," + logo_base64 + "\" class=\"header-logo-img\" alt=\"Logo\">" if logo_exists and logo_base64 else "<div class=\"header-logo-placeholder\">🗺️</div>"}
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🗺️ PETA", use_container_width=True, key="nav_peta"):
        st.session_state.current_page = "peta"
        st.rerun()
with col2:
    if st.button("📋 TENTANG", use_container_width=True, key="nav_about"):
        st.session_state.current_page = "beranda"
        st.rerun()
with col3:
    if st.button("🔐 ADMIN", use_container_width=True, key="nav_admin"):
        st.session_state.current_page = "admin"
        st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════════════
# 📍 PAGE: LANDING
# ════════════════════════════════════════════════════════════════════════════

if st.session_state.current_page == "landing":
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">🗺️ WebGIS Pemanfaatan Ruang</h1>
        <p class="hero-subtitle">Platform Geospasial Terdepan untuk Manajemen Data</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="feature-box">
            <div class="feature-icon">🗺️</div>
            <div class="feature-title">Visualisasi Interaktif</div>
            <div class="feature-desc">Peta interaktif dengan multi-layer dan filter advanced</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-box">
            <div class="feature-icon">☁️</div>
            <div class="feature-title">Google Drive Sync</div>
            <div class="feature-desc">Data otomatis tersimpan & tersinkronisasi ke Google Drive</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="feature-box">
            <div class="feature-icon">🔐</div>
            <div class="feature-title">Admin Dashboard</div>
            <div class="feature-desc">Kelola dan upload data dengan aman</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📊 Database Kami")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{len(gdf)}</div><div class="stat-label">📍 Total Data</div></div>', unsafe_allow_html=True)
    with col2:
        n = gdf["PEMANFAATAN RUANG"].nunique() if "PEMANFAATAN RUANG" in gdf.columns else 0
        st.markdown(f'<div class="stat-box"><div class="stat-number">{n}</div><div class="stat-label">🏙️ Jenis</div></div>', unsafe_allow_html=True)
    with col3:
        n = gdf["PERATURAN ZONASI"].nunique() if "PERATURAN ZONASI" in gdf.columns else 0
        st.markdown(f'<div class="stat-box"><div class="stat-number">{n}</div><div class="stat-label">📋 Zonasi</div></div>', unsafe_allow_html=True)
    with col4:
        n = gdf["TAHUN"].nunique() if "TAHUN" in gdf.columns else 0
        st.markdown(f'<div class="stat-box"><div class="stat-number">{n}</div><div class="stat-label">📅 Tahun</div></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# 📍 PAGE: PETA
# ════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_page == "peta":
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">Peta Publik Pemanfaatan Ruang</h1>
        <p class="hero-subtitle">Visualisasi & Filter Data Geospasial</p>
    </div>
    """, unsafe_allow_html=True)

    if gdf.empty:
        st.error("❌ TIDAK ADA DATA!")
        st.info("Upload data di Admin Panel atau pastikan file ada di Google Drive")
    else:
        tahun_opts = ["Semua"] + sorted(gdf["TAHUN"].dropna().astype(str).unique().tolist()) if "TAHUN" in gdf.columns else ["Semua"]
        pmnft_opts = ["Semua"] + sorted(gdf["PEMANFAATAN RUANG"].dropna().astype(str).unique().tolist()) if "PEMANFAATAN RUANG" in gdf.columns else ["Semua"]
        zona_opts = ["Semua"] + sorted(gdf["PERATURAN ZONASI"].dropna().astype(str).unique().tolist()) if "PERATURAN ZONASI" in gdf.columns else ["Semua"]

        st.markdown("**🔍 Filter Data:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.write('<p class="filter-label">📅 TAHUN</p>', unsafe_allow_html=True)
            f_tahun = st.selectbox("Tahun", tahun_opts, label_visibility="collapsed", key="tahun_filter")
        
        with col2:
            st.write('<p class="filter-label">🏙️ PEMANFAATAN</p>', unsafe_allow_html=True)
            f_pmnft = st.selectbox("Pemanfaatan", pmnft_opts, label_visibility="collapsed", key="pmnft_filter")
        
        with col3:
            st.write('<p class="filter-label">📋 ZONASI</p>', unsafe_allow_html=True)
            f_zona = st.selectbox("Zonasi", zona_opts, label_visibility="collapsed", key="zona_filter")
        
        with col4:
            st.write('<p class="filter-label">🔍 CARI</p>', unsafe_allow_html=True)
            f_kw = st.text_input("Cari Keyword", label_visibility="collapsed", placeholder="Keyword...", key="search_filter")

        fgdf = gdf.copy()
        is_filtered = False
        
        if f_tahun != "Semua": 
            fgdf = fgdf[fgdf["TAHUN"].astype(str) == f_tahun]
            is_filtered = True
        if f_pmnft != "Semua": 
            fgdf = fgdf[fgdf["PEMANFAATAN RUANG"].astype(str) == f_pmnft]
            is_filtered = True
        if f_zona != "Semua": 
            fgdf = fgdf[fgdf["PERATURAN ZONASI"].astype(str) == f_zona]
            is_filtered = True
        if f_kw:
            mask = pd.Series(False, index=fgdf.index)
            for col in ["REMARK", "KODEKBLI"]:
                if col in fgdf.columns:
                    mask |= fgdf[col].astype(str).str.contains(f_kw, case=False, na=False)
            fgdf = fgdf[mask]
            is_filtered = True

        st.markdown(f"**📊 Menampilkan {len(fgdf)} dari {len(gdf)} data**")
        if is_filtered:
            st.info("🔍 Filter aktif")

        with st.spinner("⏳ Memuat peta…"):
            center, zoom = center_map(fgdf if not fgdf.empty else gdf)

            m = leafmap.Map(
                center=center,
                zoom=zoom,
                height=500
            )

            m.add_basemap("OpenStreetMap")

            if not gdf_kabupaten.empty:
                m.add_gdf(
                    gdf_kabupaten,
                    layer_name="Batas Kabupaten",
                    style={
                        "color": "#2d6a4f",
                        "fillColor": "#2d6a4f",
                        "fillOpacity": 0.04,
                        "weight": 2.0,
                    },
                    info_mode="on_hover"
                )

            if not gdf_kecamatan.empty:
                m.add_gdf(
                    gdf_kecamatan,
                    layer_name="Batas Kecamatan",
                    style={
                        "color": "#e07b39",
                        "fillColor": "#e07b39",
                        "fillOpacity": 0.06,
                        "weight": 2.5,
                    },
                    info_mode="on_hover"
                )

            if not is_filtered and not gdf_rtrw.empty:
                m.add_gdf(
                    gdf_rtrw,
                    layer_name="RTRW",
                    style={
                        "color": "#ff6b6b",
                        "fillColor": "#ff6b6b",
                        "fillOpacity": 0.08,
                        "weight": 2.0,
                    },
                    info_mode="on_hover"
                )

            if not fgdf.empty:
                m.add_gdf(
                    fgdf,
                    layer_name="Pemanfaatan Ruang",
                    style={
                        "color": "#1a3a52",
                        "fillColor": "#FFD700",
                        "fillOpacity": 0.35,
                        "weight": 1.5,
                    },
                    info_mode="on_click"
                )

            # ── Legenda pojok kanan bawah ──────────────────────────────────
            legend_items = [
                ("Pemanfaatan Ruang", "#FFD700", "#1a3a52"),
                ("Batas Kabupaten",   "#2d6a4f", "#2d6a4f"),
                ("Batas Kecamatan",   "#e07b39", "#e07b39"),
            ]
            if not is_filtered and not gdf_rtrw.empty:
                legend_items.append(("RTRW", "#ff6b6b", "#ff6b6b"))

            legend_rows = "".join(
                f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
                f'<span style="display:inline-block;width:14px;height:14px;border-radius:3px;'
                f'background:{fill};border:2px solid {stroke};flex-shrink:0;"></span>'
                f'<span style="font-size:11px;color:#1a3a52;">{label}</span></div>'
                for label, fill, stroke in legend_items
            )

            legend_html = f"""
            <div style="
                position: fixed;
                bottom: 36px;
                right: 10px;
                z-index: 9999;
                background: rgba(255,255,255,0.92);
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                font-family: Inter, sans-serif;
                min-width: 150px;
            ">
                <div style="font-size:11px;font-weight:700;color:#1a3a52;
                            text-transform:uppercase;letter-spacing:0.5px;
                            margin-bottom:6px;border-bottom:1px solid #eee;padding-bottom:4px;">
                    Legenda
                </div>
                {legend_rows}
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

            m.to_streamlit(height=500)

        if not fgdf.empty:
            st.subheader("📋 Data Detail")
            st.dataframe(
                fgdf[display_cols(fgdf)],
                use_container_width=True,
                height=300
            )

# ════════════════════════════════════════════════════════════════════════════
# 📍 PAGE: ADMIN
# ════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_page == "admin":
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">🔐 Admin Panel</h1>
        <p class="hero-subtitle">Kelola & Upload Data Pemanfaatan Ruang</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.admin_logged_in:
        st.warning("🔒 Silakan login terlebih dahulu")
        with st.form("login_form"):
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("🔓 Login", use_container_width=True):
                if pwd == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Password salah!")
    else:
        st.success("✅ Login sebagai Admin")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.rerun()

        if drive_service:
            st.markdown('<div class="drive-status">☁️ Google Drive Sync: Aktif</div>', unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["📤 Upload Data", "📥 Export", "ℹ️ Info"])
        
        with tab1:
            st.subheader("📤 Upload Data SHP/GeoJSON")
            st.markdown("Upload file **ZIP** (berisi .shp) atau **GeoJSON** untuk mengganti/update data utama.")
            
            uploaded_file = st.file_uploader("Upload File", type=["zip", "geojson", "kml", "kmz"])
            
            if uploaded_file:
                try:
                    st.info(f"📁 File: {uploaded_file.name}")
                    shp = read_shp_from_zip(uploaded_file)
                    
                    st.success(f"✅ File valid! ({len(shp)} features)")
                    st.dataframe(shp[display_cols(shp)].head(5), use_container_width=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Ganti Seluruh Data", use_container_width=True, type="primary"):
                            with st.spinner("Menyimpan data..."):
                                save_data(shp)
                            st.rerun()
                    with col2:
                        if st.button("❌ Batal"):
                            st.rerun()
                            
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with tab2:
            st.subheader("📥 Export Data")
            
            if not gdf.empty:
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download sebagai GeoJSON",
                        gdf.to_json(),
                        "data_all.geojson",
                        "application/geo+json",
                        use_container_width=True
                    )
                with col2:
                    csv_data = gdf[display_cols(gdf)].to_csv(index=False)
                    st.download_button(
                        "📥 Download sebagai CSV",
                        csv_data,
                        "data_all.csv",
                        "text/csv",
                        use_container_width=True
                    )
        
        with tab3:
            st.subheader("ℹ️ Informasi Sistem")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📊 Total Data", len(gdf))
            with col2:
                st.metric("📁 Data File", "DATA PEMANFAATAN.geojson")
            
            st.markdown("---")
            st.markdown(f"""
            ### ☁️ Google Drive Integration
            {'✅ **Status:** Aktif' if drive_service else '❌ **Status:** Belum dikonfigurasi'}
            
            - 📂 **Folder ID:** `{FOLDER_ID}`
            - 🔗 **Link:** [Open in Drive](https://drive.google.com/drive/folders/{FOLDER_ID})
            - ⚙️ **Sinkronisasi:** Otomatis saat save
            """)

# ════════════════════════════════════════════════════════════════════════════
# 📍 PAGE: TENTANG
# ════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_page == "beranda":
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">Tentang Platform</h1>
        <p class="hero-subtitle">Solusi Geospasial untuk Pemanfaatan Ruang</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ### 📋 Tentang Platform
    
    WebGIS Pemanfaatan Ruang adalah sistem informasi geospasial yang dirancang untuk manajemen data spasial dengan integrasi Google Drive terintegrasi penuh.
    
    ### ✨ Fitur Utama
    
    - 🗺️ **Visualisasi Peta Interaktif** - Multi-layer dengan Folium
    - 🔍 **Filter Data Advanced** - Filter berdasarkan tahun, pemanfaatan, zonasi
    - 📤 **Upload Data** - Support SHP, GeoJSON, KML, KMZ
    - ☁️ **Google Drive Integration** - Auto-load & auto-backup
    - 🔐 **Admin Panel** - Password-protected untuk data management
    - 📊 **Data Export** - Download sebagai GeoJSON atau CSV
    """)

# ════════════════════════════════════════════════════════════════════════════
# 🔚 FOOTER
# ════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div class="footer">
    <p>© 2025 WebGIS Pemanfaatan Ruang — Platform Geospasial Terdepan</p>
    <p style="font-size: 0.8rem;">Dengan Google Drive Integration ☁️ | Data di-load langsung dari Drive</p>
</div>
""", unsafe_allow_html=True)
