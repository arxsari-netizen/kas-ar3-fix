import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. SETTING DASAR ---
st.set_page_config(page_title="AR-ROYHAAN 3", layout="wide")

# --- 2. LOGIN SYSTEM (STRICT) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

if not st.session_state['logged_in']:
    st.title("🔐 Login AR-ROYHAAN 3")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk"):
            if u == st.secrets["users"]["admin_user"] and p == st.secrets["users"]["admin_password"]:
                st.session_state.update({"logged_in": True, "role": "admin"})
                st.rerun()
            elif u == st.secrets["users"]["warga_user"] and p == st.secrets["users"]["warga_password"]:
                st.session_state.update({"logged_in": True, "role": "user"})
                st.rerun()
            else:
                st.error("Gagal!")
    st.stop()

# --- 3. DATA ENGINE ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=60)
def load_all_sheets():
    # Load semua sheet sekaligus biar gak bolak-balik
    pemasukan = pd.DataFrame(sh.worksheet("Pemasukan").get_all_records())
    pengeluaran = pd.DataFrame(sh.worksheet("Pengeluaran").get_all_records())
    warga = pd.DataFrame(sh.worksheet("Warga").get_all_records())
    event = pd.DataFrame(sh.worksheet("Event").get_all_records())
    
    # Casting angka biar gak error
    for df in [pemasukan, pengeluaran, event]:
        for col in ['Kas', 'Hadiah', 'Total', 'Jumlah', 'Tahun']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return pemasukan, pengeluaran, warga, event

df_masuk, df_keluar, df_warga, df_event = load_all_sheets()

# --- 4. SIDEBAR NAVIGASI (HANYA SATU TEMPAT) ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=80)
    st.write(f"Logged in as: **{st.session_state['role']}**")
    st.divider()
    
    # Definisi menu berdasarkan Role
    if st.session_state['role'] == "admin":
        menu_options = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event", "📤 Pengeluaran", "👥 Warga", "📜 Log"]
    else:
        menu_options = ["📊 Laporan", "📜 Log"]
    
    # INI YANG BIKIN NAVIGASI MUNCUL TERUS
    choice = st.radio("MENU UTAMA", menu_options)
    
    st.divider()
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# --- 5. LOGIKA DASHBOARD (TAMPIL DI SEMUA MENU) ---
st.header(f"AR-ROYHAAN 3 - {choice}")

# --- 6. ROUTING HALAMAN ---

if choice == "📊 Laporan":
    st.subheader("📋 Rekapitulasi Dana")
    tab_kas, tab_event = st.tabs(["💰 Kas & Hadiah", "🎭 Event"])
    
    with tab_kas:
        # TAHUN FILTER
        thn = st.selectbox("Pilih Tahun", [2024, 2025, 2026], index=1)
        df_y = df_masuk[df_masuk['Tahun'] == thn]
        bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

        # TABEL 1: KAS (15rb)
        st.markdown("### 🟢 LAPORAN KAS (15.000)")
        if not df_y.empty:
            rk_kas = df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            st.dataframe(rk_kas.reindex(columns=[b for b in bln_order if b in rk_kas.columns], fill_value=0), use_container_width=True)
        
        st.divider()

        # TABEL 2: HADIAH (35rb)
        st.markdown("### 🟡 LAPORAN HADIAH (35.000)")
        if not df_y.empty:
            rk_hadiah = df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            st.dataframe(rk_hadiah.reindex(columns=[b for b in bln_order if b in rk_hadiah.columns], fill_value=0), use_container_width=True)

elif choice == "📥 Kas Bulanan":
    st.info("Input Pembayaran Kas & Hadiah (Otomatis Pecah 15/35)")
    with st.form("input_kas"):
        nama = st.selectbox("Nama Warga", df_warga['Nama'].tolist())
        nominal = st.number_input("Nominal Bayar", min_value=0, step=5000)
        tahun = st.selectbox("Tahun", [2025, 2026])
        bulan = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        
        if st.form_submit_button("Simpan Data"):
            # Logika pembagian 15/35
            v_kas = 15000 if nominal >= 15000 else nominal
            v_hadiah = nominal - v_kas
            
            new_row = [datetime.now().strftime("%d/%m/%Y"), nama, tahun, bulan, nominal, v_kas, v_hadiah, "LUNAS", "Manual"]
            sh.worksheet("Pemasukan").append_row(new_row)
            st.success("Tersimpan!")
            st.cache_data.clear()
            st.rerun()

elif choice == "🎭 Event":
    st.info("Iuran Khusus Event/Kegiatan")
    with st.form("input_event"):
        ev_name = st.text_input("Nama Event (Contoh: Mancing)")
        warga = st.selectbox("Penyetor", df_warga['Nama'].tolist())
        jml = st.number_input("Nominal", min_value=0)
        if st.form_submit_button("Simpan Iuran"):
            sh.worksheet("Event").append_row([datetime.now().strftime("%d/%m/%Y"), warga, ev_name, jml])
            st.success("OK!")
            st.cache_data.clear()
            st.rerun()

elif choice == "📤 Pengeluaran":
    with st.form("out"):
        kat = st.selectbox("Ambil Dana Dari", ["Kas", "Hadiah", "Event"])
        nom_out = st.number_input("Nominal Keluar", min_value=0)
        ket = st.text_input("Keterangan")
        if st.form_submit_button("Catat"):
            sh.worksheet("Pengeluaran").append_row([datetime.now().strftime("%d/%m/%Y"), kat, nom_out, ket])
            st.success("Tercatat!")
            st.cache_data.clear()
            st.rerun()

elif choice == "👥 Warga":
    st.subheader("Data Warga")
    with st.form("warga"):
        n_warga = st.text_input("Nama Warga Baru")
        if st.form_submit_button("Tambah"):
            sh.worksheet("Warga").append_row([n_warga, "Main Warga"])
            st.rerun()
    st.table(df_warga)

elif choice == "📜 Log":
    st.subheader("Log Transaksi")
    st.dataframe(df_masuk.tail(15), use_container_width=True)
