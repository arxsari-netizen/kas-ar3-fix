import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="KAS AR3 ONLINE", 
    page_icon="🏦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Custom untuk tampilan HP lebih rapi
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNGSI AMBIL DATA (MODE STABIL CSV) ---
def load_data():
    try:
        # Mengambil URL dari Secrets
        if "connections" not in st.secrets:
            st.error("Konfigurasi Secrets (Link Google Sheets) belum diisi!")
            st.stop()
            
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # Membersihkan URL agar menjadi link ekspor CSV
        clean_url = raw_url.split("/edit")[0].split("/view")[0]
        csv_base = f"{clean_url}/export?format=csv"
        
        # Baca tiap Sheet (Tab)
        # gid=0 adalah tab pertama (Pemasukan)
        df_m = pd.read_csv(f"{csv_base}&gid=0")
        # Menggunakan nama sheet untuk tab lainnya
        df_k = pd.read_csv(f"{csv_base}&sheet=Pengeluaran")
        df_w = pd.read_csv(f"{csv_base}&sheet=Warga")
        
        # Bersihkan spasi di nama kolom agar tidak KeyError
        df_m.columns = df_m.columns.str.strip()
        df_k.columns = df_k.columns.str.strip()
        df_w.columns = df_w.columns.str.strip()
        
        # Penanganan Tanggal
        if 'Tanggal' in df_m.columns:
            df_m['Tanggal_Obj'] = pd.to_datetime(df_m['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        
        return df_m, df_k, df_w
    except Exception as e:
        st.error(f"⚠️ Gagal Memuat Data. Cek Nama Tab & Link GSheets. Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 3. LOGIKA HITUNG OTOMATIS (SINKRON KE GOOGLE SHEETS) ---
def hitung_pembayaran(nama, nominal, thn, bln_mulai, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx = list_bulan.index(bln_mulai)
    sisa = nominal
    data_baru = []
    
    while sisa > 0:
        bulan_skrg = list_bulan[idx]
        if role == "Main Warga":
            # Cek riwayat iuran
            kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == bulan_skrg) & (df_existing
