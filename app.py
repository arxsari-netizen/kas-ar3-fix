import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Kas AR3 Online", layout="wide")

# --- KONEKSI DATABASE (CARA STABIL) ---
# Ambil URL dari Secrets
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # Ubah link /edit menjadi /export?format=csv
    CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"
except:
    st.error("Konfigurasi Secrets GSheets belum benar!")
    st.stop()

def load_data():
    try:
        # Baca tiap tab lewat parameter gid (GSheets standard)
        # GID: Pemasukan=0, Pengeluaran=???, Warga=??? 
        # TAPI paling aman pakai link export per worksheet:
        df_m = pd.read_csv(f"{CSV_URL}&gid=0") # Tab pertama biasanya gid=0
        df_k = pd.read_csv(f"{CSV_URL}&sheet=Pengeluaran")
        df_w = pd.read_csv(f"{CSV_URL}&sheet=Warga")
        
        df_m['Tanggal_Obj'] = pd.to_datetime(df_m['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        return df_m, df_k, df_w
    except Exception as e:
        st.warning(f"Menunggu data... (Pastikan Header di GSheets sudah ada). Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- SISANYA TETAP SAMA ---
df_masuk, df_keluar, df_warga = load_data()
st.title("📊 Kas AR3 - Jalur Stabil")
st.write("Jika data muncul di bawah, berarti koneksi sukses!")
st.dataframe(df_warga)
