import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Konfigurasi Halaman
st.set_page_config(page_title="Kas AR3 Online", layout="wide")

# Inisialisasi Koneksi
conn = st.connection("gsheets", type=GSheetsConnection)

# Fungsi Load Data
def load_data():
    try:
        df_m = conn.read(worksheet="Pemasukan", ttl=0).dropna(how='all')
        df_k = conn.read(worksheet="Pengeluaran", ttl=0).dropna(how='all')
        df_w = conn.read(worksheet="Warga", ttl=0).dropna(how='all')
        
        # Konversi Tanggal untuk Sorting
        df_m['Tanggal_Obj'] = pd.to_datetime(df_m['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        return df_m, df_k, df_w
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Pastikan Nama Sheet & URL benar. Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Fungsi Simpan Data
def save_data(df_m, df_k, df_w):
    # Hapus kolom pembantu sebelum simpan
    df_m_save = df_m.drop(columns=['Tanggal_Obj'], errors='ignore')
    conn.update(worksheet="Pemasukan", data=df_m_save)
    conn.update(worksheet="Pengeluaran", data=df_k)
    conn.update(worksheet="Warga", data=df_w)
    st.cache_data.clear()
    st.toast("✅ Data Tersinkron ke Google Drive!")

# Ambil Data
df_masuk, df_keluar, df_warga = load_data()

# --- BAGIAN DASHBOARD (TETAP SAMA) ---
st.title("📊 Kas Majelis AR3 Online")
if not df_masuk.empty:
    in_k = df_masuk['Kas'].sum()
    in_h = df_masuk['Hadiah'].sum()
    out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum() if not df_keluar.empty else 0
    out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum() if not df_keluar.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
    c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
    c3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")

st.divider()

# Menu Navigasi
menu = st.sidebar.radio("Navigasi", ["📥 Input Masuk", "📤 Input Keluar", "📊 Laporan", "👥 Kelola Warga", "📜 Log"])

# (Sama seperti logika sebelumnya untuk Input, Laporan, dll...)
# Pastikan setiap ada penambahan data, panggil save_data(df_masuk, df_keluar, df_warga)
