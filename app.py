import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURASI TAMPILAN (Agar Terasa Seperti Aplikasi APK) ---
st.set_page_config(
    page_title="KAS AR3 ONLINE",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed" # Sidebar tertutup di HP agar lega
)

# Menghilangkan padding berlebih agar rapi di layar HP
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Menggunakan metode pembacaan stabil lewat link CSV internal
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = url.split("/edit")[0] + "/export?format=csv"
        
        # Baca 3 tab wajib
        df_m = pd.read_csv(f"{csv_url}&sheet=Pemasukan")
        df_k = pd.read_csv(f"{csv_url}&sheet=Pengeluaran")
        df_w = pd.read_csv(f"{csv_url}&sheet=Warga")
        
        # Pembersihan data
        df_m = df_m.dropna(how='all')
        df_k = df_k.dropna(how='all')
        df_w = df_w.dropna(how='all')

        if not df_m.empty:
            df_m['Tanggal_Obj'] = pd.to_datetime(df_m['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        
        return df_m, df_k, df_w
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def save_data(df_m, df_k, df_w):
    df_m_save = df_m.drop(columns=['Tanggal_Obj'], errors='ignore')
    try:
        conn.update(worksheet="Pemasukan", data=df_m_save)
        conn.update(worksheet="Pengeluaran", data=df_k)
        conn.update(worksheet="Warga", data=df_w)
        st.cache_data.clear()
        st.toast("✅ Data Tersimpan ke Cloud!")
    except Exception as e:
        st.error(f"Gagal Sinkron: {e}")

# --- 3. LOGIKA PEMBAYARAN AUTOMATIS ---
def proses_bayar(nama, nominal, thn, bln, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx_bln = list_bulan.index(bln)
    sisa = nominal
    data_baru = []
    
    while sisa > 0:
        curr_bln = list_bulan[idx_bln]
        if role == "Main Warga":
            kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == curr_bln) & (df_existing['Tahun'] == thn)
            sdh_bayar = df_existing[kondisi]['Total'].sum() if not df_existing[kondisi].empty else 0
            sdh_kas = df_existing[kondisi]['Kas'].sum() if not df_existing[kondisi].empty else 0
