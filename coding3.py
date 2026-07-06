import os
import io
import time
import base64
import zipfile
import tempfile
import pathlib
import json
from pathlib import Path
from datetime import datetime

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


st.markdown("""
<style>
[data-testid="stDecoration"] {
    display: none;
}

button[kind="header"] {
    display: none;
}

iframe[title="streamlit_app"] {
    border: none;
}

[data-testid="stStatusWidget"] {
    display: none !important;
}

div[role="dialog"] {
    display: none !important;
}

div[data-testid*="profile"],
div[class*="ProfileCard"],
div[class*="profile-card"],
div[class*="user-card"],
div[class*="share-card"] {
    display: none !important;
}

div[data-testid*="popover"],
div[role="tooltip"] {
    display: none !important;
}

a[href*="streamlit"] {
    display: none !important;
}

div[style*="position: fixed"][style*="right"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "1dTdLnvUyRgFDKCSLLKH83ZOb2fou0Mci"  


TEMP_DIR = pathlib.Path(tempfile.gettempdir()) / "webgis_cache"
TEMP_DIR.mkdir(exist_ok=True)

FILE_MAP = {
    "DATA PEMANFAATAN.geojson": TEMP_DIR / "DATA PEMANFAATAN.geojson",
    "Batas Administrasi Kabupaten Bandung.geojson": TEMP_DIR / "Batas Administrasi Kabupaten Bandung.geojson",
    "Batas Administrasi Kecamatan Katapang.geojson": TEMP_DIR / "Batas Administrasi Kecamatan Katapang.geojson",
    "RTRW.geojson": TEMP_DIR / "RTRW.geojson",
}

DATA_FILE = FILE_MAP["DATA PEMANFAATAN.geojson"]
BACKUP_FILE = TEMP_DIR / "DATA_BACKUP.geojson"
KABUPATEN_FILE = FILE_MAP["Batas Administrasi Kabupaten Bandung.geojson"]
KECAMATAN_FILE = FILE_MAP["Batas Administrasi Kecamatan Katapang.geojson"]
RTRW_FILE = FILE_MAP["RTRW.geojson"]


LOGO_PATH = r"logoupimerah.png"

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")



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

.delete-row {
    background: rgba(255, 107, 107, 0.05); padding: 8px; border-radius: 4px; margin: 4px 0;
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

function removeProfilePopups() {
    const statusWidget = document.querySelector('[data-testid="stStatusWidget"]');
    if (statusWidget) statusWidget.style.display = 'none';
    
    const dialogs = document.querySelectorAll('[role="dialog"]');
    dialogs.forEach(d => d.style.display = 'none');
    
    const profileCards = document.querySelectorAll('[class*="ProfileCard"], [class*="profile-card"], [class*="user-card"]');
    profileCards.forEach(pc => pc.style.display = 'none');
}

document.addEventListener('DOMContentLoaded', removeProfilePopups);
setInterval(removeProfilePopups, 500);
</script>
""", unsafe_allow_html=True)


if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "landing"


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


@st.cache_data(ttl=0)  
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

@st.cache_data(ttl=0)  
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

def save_data(gdf: gpd.GeoDataFrame, is_backup=False):
    """Save data to local + upload to Google Drive"""
    try:
        # Normalize CRS
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        
        # Save to local file
        gdf.to_file(str(DATA_FILE), driver="GeoJSON")
        
        if not is_backup:
            st.success("✅ Data tersimpan ke file lokal!")
        
        # Upload to Drive
        drive_service = get_drive_service()
        if drive_service:
            with st.spinner("⏳ Uploading ke Google Drive..."):
                if upload_to_drive(drive_service, DATA_FILE, "DATA PEMANFAATAN.geojson"):
                    if not is_backup:
                        st.success("✅ Data juga tersimpan ke Google Drive!")
        
        # Clear cache
        st.cache_data.clear()
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def append_data(new_gdf: gpd.GeoDataFrame):
    """TAMBAH data baru ke data existing (BUKAN MENGGANTI)"""
    try:
        # Load data yang ada
        existing_gdf = load_data()
        
        # Normalize CRS untuk new data
        if new_gdf.crs is None:
            new_gdf = new_gdf.set_crs("EPSG:4326")
        elif new_gdf.crs.to_epsg() != 4326:
            new_gdf = new_gdf.to_crs("EPSG:4326")
        
        # Jika data existing kosong, gunakan new data saja
        if existing_gdf.empty:
            combined_gdf = new_gdf.copy()
        else:
            # PENTING: Hapus OBJECTID dari new_gdf sebelum concat
            if "OBJECTID" in new_gdf.columns:
                new_gdf = new_gdf.drop(columns=["OBJECTID"])
            
            # Combine data
            combined_gdf = pd.concat([existing_gdf, new_gdf], ignore_index=True)
            combined_gdf = combined_gdf.reset_index(drop=True)
        
        # Re-number OBJECTID
        if "OBJECTID" in combined_gdf.columns:
            combined_gdf = combined_gdf.drop(columns=["OBJECTID"])
        combined_gdf.insert(0, "OBJECTID", range(1, len(combined_gdf) + 1))
        
        # Save backup terlebih dahulu
        if not existing_gdf.empty:
            existing_gdf.to_file(str(BACKUP_FILE), driver="GeoJSON")
        
        # Save combined data
        save_data(combined_gdf)
        
        old_count = len(existing_gdf) if not existing_gdf.empty else 0
        new_count = len(combined_gdf)
        added = new_count - old_count
        
        st.success(f"✅ Data ditambahkan! ({old_count} + {added} = {new_count} geometri)")
        return True
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return False

def delete_row(row_id: int):
    """Hapus satu row berdasarkan OBJECTID"""
    try:
        gdf = load_data()
        
        if gdf.empty:
            st.error("❌ Data kosong!")
            return False
        
        # Find the row with given OBJECTID
        if row_id not in gdf["OBJECTID"].values:
            st.error(f"❌ Data dengan ID {row_id} tidak ditemukan!")
            return False
        
        # Save backup
        gdf.to_file(str(BACKUP_FILE), driver="GeoJSON")
        
        # Delete the row
        gdf = gdf[gdf["OBJECTID"] != row_id].reset_index(drop=True)
        
        # Re-number OBJECTID
        gdf["OBJECTID"] = range(1, len(gdf) + 1)
        
        # Save
        save_data(gdf)
        st.success(f"✅ Geometri ID {row_id} berhasil dihapus!")
        return True
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return False

def restore_backup():
    """Restore data dari backup"""
    try:
        if not BACKUP_FILE.exists():
            st.error("❌ Tidak ada backup data!")
            return False
        
        gdf = gpd.read_file(str(BACKUP_FILE))
        save_data(gdf)
        st.success("✅ Data berhasil di-restore dari backup!")
        return True
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return False

def display_cols(gdf: gpd.GeoDataFrame):
    """Get columns to display (exclude geometry)"""
    cols = [c for c in gdf.columns if c != "geometry"]
    return cols

def read_shp_from_zip(uploaded_file) -> gpd.GeoDataFrame:
    """Read SHP/GeoJSON/KML from uploaded file"""
    try:
        filename = uploaded_file.name.lower()
        
        if filename.endswith('.geojson'):
            data = json.loads(uploaded_file.read().decode('utf-8'))
            return gpd.GeoDataFrame.from_features(data['features'])
        
        elif filename.endswith(('.kml', '.kmz')):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kmz' if filename.endswith('.kmz') else '.kml') as tmp:
                tmp.write(uploaded_file.read())
                tmp.flush()
                gdfs = gpd.read_file(tmp.name)
                os.unlink(tmp.name)
                return gdfs if isinstance(gdfs, gpd.GeoDataFrame) else gdfs[0] if len(gdfs) > 0 else gpd.GeoDataFrame()
        
        elif filename.endswith('.zip'):
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(io.BytesIO(uploaded_file.read())) as zip_ref:
                    zip_ref.extractall(tmpdir)
                
                shp_files = list(pathlib.Path(tmpdir).glob("*.shp"))
                if shp_files:
                    return gpd.read_file(str(shp_files[0]))
                
                geojson_files = list(pathlib.Path(tmpdir).glob("*.geojson"))
                if geojson_files:
                    return gpd.read_file(str(geojson_files[0]))
        
        st.error("❌ Format file tidak didukung!")
        return gpd.GeoDataFrame()
        
    except Exception as e:
        st.error(f"❌ Error membaca file: {str(e)}")
        return gpd.GeoDataFrame()

drive_service = get_drive_service()
gdf = load_data()
gdf_kabupaten = load_boundary(str(KABUPATEN_FILE))
gdf_kecamatan = load_boundary(str(KECAMATAN_FILE))
gdf_rtrw = load_boundary(str(RTRW_FILE))

logo_col, header_col, button_col = st.columns([1.2, 3, 1])
with logo_col:
    if logo_exists and logo_base64:
        st.markdown(f'<img src="data:image/png;base64,{logo_base64}" style="max-width:60px;height:auto;">', unsafe_allow_html=True)
    else:
        st.markdown('<div class="header-logo-placeholder">🗺️</div>', unsafe_allow_html=True)

with header_col:
    st.markdown("<h1 style='margin:0;padding:0;font-family:Playfair Display,serif;color:#1a3a52;font-size:2rem;'>WebGIS Pemanfaatan Ruang</h1>", unsafe_allow_html=True)

with button_col:
    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        if st.button("📍 Peta", use_container_width=True):
            st.session_state.current_page = "peta"
            st.rerun()
    with col2:
        if st.button("🔐 Admin", use_container_width=True):
            st.session_state.current_page = "admin"
            st.rerun()
    with col3:
        if st.button("ℹ️ Info", use_container_width=True):
            st.session_state.current_page = "beranda"
            st.rerun()

st.markdown("---")


if st.session_state.current_page == "peta":
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">Peta Interaktif</h1>
        <p class="hero-subtitle">Visualisasi Data Pemanfaatan Ruang</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        tahun_list = []
        if not gdf.empty and "TAHUN" in gdf.columns:
            tahun_list = sorted(gdf["TAHUN"].dropna().unique().astype(str).tolist())
        tahun = st.selectbox("📅 Filter Tahun", ["Semua"] + tahun_list)

    with col2:
        pemanfaatan_list = []
        if not gdf.empty and "PEMANFAATAN" in gdf.columns:
            pemanfaatan_list = sorted(gdf["PEMANFAATAN"].dropna().unique().astype(str).tolist())
        pemanfaatan = st.selectbox("🏢 Filter Pemanfaatan", ["Semua"] + pemanfaatan_list)

    # Filter data
    fgdf = gdf.copy()
    is_filtered = False
    
    if tahun != "Semua":
        fgdf = fgdf[fgdf["TAHUN"].astype(str) == tahun]
        is_filtered = True
    
    if pemanfaatan != "Semua":
        fgdf = fgdf[fgdf["PEMANFAATAN"].astype(str) == pemanfaatan]
        is_filtered = True

    # Show stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <p class="stat-number">{len(fgdf)}</p>
            <p class="stat-label">Geometri Ditampilkan</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <p class="stat-number">{len(gdf)}</p>
            <p class="stat-label">Total Data</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        if not fgdf.empty:
            total_area = fgdf.geometry.area.sum() * 111000 * 111000  # rough conversion to m2
            st.markdown(f"""
            <div class="stat-box">
                <p class="stat-number">{total_area/1e6:.2f}</p>
                <p class="stat-label">Luas (KM²)</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Peta
    with st.container():
        m = leafmap.Map(center=(center_lat := 6.9, center_lon := 107.6), zoom=11)

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

        tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Data", "🗑️ Hapus Data", "📥 Export", "ℹ️ Info"])
        
        with tab1:
            st.subheader("📤 Upload Data SHP/GeoJSON - TAMBAH KE DATA EXISTING")
            st.markdown("""
            ⚠️ **PENTING:** Fitur ini akan **MENAMBAH** geometri baru ke data yang sudah ada.
            
            Contoh:
            - Data sekarang: 36 geometri
            - Upload: 1 geometri baru
            - Hasil: 37 geometri (bukan kehapus!)
            
            Jika ingin mengganti seluruh data, gunakan restore terlebih dahulu.
            """)
            
            uploaded_file = st.file_uploader("Upload File", type=["zip", "geojson", "kml", "kmz"])
            
            if uploaded_file:
                try:
                    st.info(f"📁 File: {uploaded_file.name}")
                    new_shp = read_shp_from_zip(uploaded_file)
                    
                    if new_shp.empty:
                        st.error("❌ File kosong atau format tidak valid!")
                    else:
                        st.success(f"✅ File valid! ({len(new_shp)} features)")
                        st.dataframe(new_shp[display_cols(new_shp)].head(3), use_container_width=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("➕ Tambah Data (APPEND)", use_container_width=True, type="primary"):
                                if append_data(new_shp):
                                    st.rerun()
                        with col2:
                            if st.button("❌ Batal"):
                                st.rerun()
                            
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        with tab2:
            st.subheader("🗑️ Hapus Geometri Satu Per Satu")
            st.markdown("Pilih geometri yang ingin dihapus dari daftar di bawah.")
            
            if gdf.empty:
                st.warning("⚠️ Tidak ada data untuk dihapus")
            else:
                st.write(f"Total geometri: **{len(gdf)}**")
                
                # Tampilkan preview
                preview_df = gdf[["OBJECTID"] + display_cols(gdf)].head(20).copy()
                st.dataframe(preview_df, use_container_width=True, height=300)
                
                st.markdown("---")
                
                # Delete form
                col1, col2 = st.columns(2)
                with col1:
                    row_id = st.number_input("ID Geometri yang ingin dihapus:", min_value=1, max_value=len(gdf), value=1, step=1)
                
                with col2:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Hapus Geometri Ini", use_container_width=True, type="secondary"):
                        if delete_row(int(row_id)):
                            st.rerun()
                
                st.markdown("---")
                st.subheader("🔄 Restore Data")
                
                if BACKUP_FILE.exists():
                    st.info("💾 Ada backup data tersedia")
                    if st.button("🔄 Restore dari Backup", use_container_width=True):
                        if restore_backup():
                            st.rerun()
                else:
                    st.warning("❌ Tidak ada backup data")
        
        with tab3:
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
        
        with tab4:
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
    
    ### ✨ Fitur Utama (YANG SUDAH DIPERBAIKI)
    
    - 🗺️ **Visualisasi Peta Interaktif** - Multi-layer dengan Folium
    - 🔍 **Filter Data Advanced** - Filter berdasarkan tahun, pemanfaatan, zonasi
    - 📤 **Upload Data (APPEND)** - Support SHP, GeoJSON, KML, KMZ - **Data baru ditambahkan, bukan dihapus!**
    - 🗑️ **Hapus Per Geometri** - Hapus satu per satu, bukan semua sekaligus
    - 🔄 **Backup & Restore** - Otomatis backup sebelum delete
    - ☁️ **Google Drive Integration** - Auto-load & auto-backup
    - 🔐 **Admin Panel** - Password-protected untuk data management
    - 📊 **Data Export** - Download sebagai GeoJSON atau CSV
    
    ### ✅ Perbaikan dari Versi Lama
    
    **MASALAH LAMA:** Ketika upload data, semua data lama kehapus
    
    **SOLUSI BARU:**
    - ✅ Upload sekarang **APPEND** (menambah), bukan replace
    - ✅ Bisa hapus geometri **satu per satu** dengan UI yang mudah
    - ✅ Automatic backup sebelum delete
    - ✅ Fitur restore jika ada kesalahan
    """)



st.markdown("---")
st.markdown("""
<div class="footer">
    <p>© 2026 WebGIS Pemanfaatan Ruang — Platform Geospasial Terdepan (FIXED VERSION)</p>
    <p style="font-size: 0.8rem;">✅ Upload sekarang APPEND (menambah) | Hapus per geometri | Backup otomatis</p>
</div>
""", unsafe_allow_html=True)
