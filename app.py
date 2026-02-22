import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. CONFIG HALAMAN ---
st.set_page_config(
    page_title="AR-ROYHAAN 3 KAS & EVENT",
    page_icon="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png",
    layout="wide"
)

# --- 2. CSS CUSTOM (BIAR RAPI) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEM LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

def login():
    _, col_mid, _ = st.columns([0.1, 1, 0.1])
    with col_mid:
        st.markdown("""
            <div style="text-align: center; border: 2px solid #D4AF37; padding: 20px; border-radius: 15px; background: white;">
                <h3>AR-ROYHAAN 3</h3>
                <p>LOGIN SYSTEM</p>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                u_data = st.secrets["users"]
                if user == u_data.get("admin_user") and pwd == u_data.get("admin_password"):
                    st.session_state.update({"logged_in": True, "role": "admin"})
                    st.rerun()
                elif user == u_data.get("warga_user") and pwd == u_data.get("warga_password"):
                    st.session_state.update({"logged_in": True, "role": "user"})
                    st.rerun()
                else: st.error("Username/Password salah")

if not st.session_state['logged_in']:
    login()
    st.stop()

# --- 4. KONEKSI GOOGLE SHEETS ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=60)
def load_data(sheet_name):
    try:
        worksheet = sh.worksheet(sheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
        for col in ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def append_to_cloud(sheet_name, df_new):
    sh.worksheet(sheet_name).append_rows(df_new.values.tolist())
    st.cache_data.clear()

# --- 5. LOGIKA NAVIGASI (DITARUH DI ATAS AGAR SELALU MUNCUL) ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=80)
    st.title("NAVIGASI")
    
    # Hak akses menu
    if st.session_state['role'] == "admin":
        list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"]
    else:
        list_menu = ["📊 Laporan", "📜 Log"]
    
    menu = st.radio("Pilih Menu:", list_menu)
    st.divider()
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
    if st.button("🚪 Logout"): st.session_state.clear(); st.rerun()

# LOAD SEMUA DATA
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")
df_event = load_data("Event")

# --- 6. DASHBOARD RINGKASAN ---
st.title(f"🏦 AR-ROYHAAN 3 - {menu}")
c1, c2, c3 = st.columns(3)
c1.metric("💰 Kas (15rb)", f"Rp {df_masuk['Kas'].sum() - df_keluar[df_keluar['Kategori']=='Kas']['Jumlah'].sum():,.0f}")
c2.metric("🎁 Hadiah (35rb)", f"Rp {df_masuk['Hadiah'].sum() - df_keluar[df_keluar['Kategori']=='Hadiah']['Jumlah'].sum():,.0f}")
c3.metric("🎭 Event", f"Rp {df_event['Jumlah'].sum() - df_keluar[df_keluar['Kategori']=='Event']['Jumlah'].sum():,.0f}")
st.divider()

# --- 7. LOGIKA KONTEN ---

if menu == "📊 Laporan":
    tab1, tab2 = st.tabs(["💰 Kas & Hadiah Bulanan", "🎭 Detail Event"])
    with tab1:
        thn = st.selectbox("Tahun", [2024, 2025, 2026], index=1)
        bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        df_y = df_masuk[df_masuk['Tahun'] == thn]
        
        st.subheader("🟢 Laporan Kas (Wajib 15.000)")
        if not df_y.empty:
            rk_k = df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            st.dataframe(rk_k.reindex(columns=[b for b in bln_order if b in rk_k.columns]).style.format("{:,.0f}"))
        
        st.subheader("🟡 Laporan Hadiah (Wajib 35.000)")
        if not df_y.empty:
            rk_h = df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            st.dataframe(rk_h.reindex(columns=[b for b in bln_order if b in rk_h.columns]).style.format("{:,.0f}"))

elif menu == "📥 Kas Bulanan":
    with st.form("input_kas"):
        nw = st.selectbox("Warga", sorted(df_warga['Nama'].tolist()))
        nom = st.number_input("Nominal", min_value=0, step=5000)
        th_in = st.selectbox("Tahun", [2025, 2026])
        bl_in = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        if st.form_submit_button("Simpan"):
            # Logika pecah 15rb/35rb sederhana
            p_kas = min(nom, 15000)
            p_hadiah = nom - p_kas
            new_data = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y"), 'Nama': nw, 'Tahun': th_in, 'Bulan': bl_in, 'Total': nom, 'Kas': p_kas, 'Hadiah': p_hadiah, 'Status': 'LUNAS'}])
            append_to_cloud("Pemasukan", new_data)
            st.success("Berhasil!")
            st.rerun()

elif menu == "🎭 Event & Iuran":
    with st.form("input_ev"):
        ev_nm = st.text_input("Nama Event")
        w_nm = st.selectbox("Warga", sorted(df_warga['Nama'].tolist()))
        jml = st.number_input("Jumlah", min_value=0)
        if st.form_submit_button("Simpan Iuran Event"):
            new_ev = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y"), 'Nama': w_nm, 'Nama Event': ev_nm, 'Jumlah': jml}])
            append_to_cloud("Event", new_ev)
            st.success("Event Tersimpan!")
            st.rerun()

elif menu == "📤 Pengeluaran":
    with st.form("input_out"):
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah", "Event"])
        jml_out = st.number_input("Nominal", min_value=0)
        ket = st.text_input("Keterangan")
        if st.form_submit_button("Catat Pengeluaran"):
            new_out = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y"), 'Kategori': kat, 'Jumlah': jml_out, 'Keterangan': ket}])
            append_to_cloud("Pengeluaran", new_out)
            st.success("Pengeluaran Dicatat!")
            st.rerun()

elif menu == "👥 Kelola Warga":
    nw_warga = st.text_input("Nama Warga Baru")
    if st.button("Tambah Warga"):
        new_w = pd.DataFrame([{'Nama': nw_warga, 'Role': 'Main Warga'}])
        append_to_cloud("Warga", new_w)
        st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.write("### 20 Transaksi Terakhir")
    st.dataframe(df_masuk.tail(20))
