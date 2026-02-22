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

# --- 2. CSS GLOBAL (GOLD THEME) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #D4AF37 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEM LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

def login():
    _, col_mid, _ = st.columns([0.1, 1, 0.1])
    with col_mid:
        st.markdown(f"""
            <div style="text-align: center; border: 2px solid #D4AF37; padding: 20px; border-radius: 15px; background: white;">
                <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="60">
                <h3 style="margin:10px 0 0 0;">AR-ROYHAAN 3</h3>
                <p style="color:#B8860B; font-weight:700;">MANAGEMENT KAS & EVENT</p>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk Ke Aplikasi"):
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

# --- 4. DATA ENGINE ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=60)
def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    df = pd.DataFrame(worksheet.get_all_records())
    for col in ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']:
        if col in df.columns: 
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def append_to_cloud(sheet_name, df_new):
    sh.worksheet(sheet_name).append_rows(df_new.values.tolist())
    st.cache_data.clear()

def rewrite_cloud(sheet_name, df_full):
    ws = sh.worksheet(sheet_name)
    ws.clear()
    ws.update([df_full.columns.values.tolist()] + df_full.values.tolist())
    st.cache_data.clear()

# LOAD DATA
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")
df_event = load_data("Event")

# --- 5. SIDEBAR NAVIGASI (LOCK) ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=100)
    st.markdown(f"**👤 ROLE: {st.session_state['role'].upper()}**")
    st.divider()
    
    if st.session_state['role'] == "admin":
        list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"]
    else:
        list_menu = ["📊 Laporan", "📜 Log"]
    
    menu = st.radio("NAVIGASI UTAMA", list_menu)
    st.divider()
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
    if st.button("🚪 Logout"): st.session_state.clear(); st.rerun()

# --- 6. DASHBOARD METRIK (SELALU MUNCUL) ---
st.markdown(f"## 🏦 DASHBOARD KEUANGAN")
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
in_ev = df_event['Jumlah'].sum() if not df_event.empty else 0
out_ev = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
m3.metric("🎭 SALDO EVENT", f"Rp {in_ev - out_ev:,.0f}")
m4.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h+in_ev)-(out_k+out_h+out_ev):,.0f}")
st.divider()

# --- 7. ROUTING MENU ---

if menu == "📊 Laporan":
    st.subheader("📋 Laporan Kas & Event")
    tab1, tab2 = st.tabs(["💰 Kas & Hadiah Bulanan", "🎭 Detail Event"])
    
    with tab1:
        thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
        bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        df_yr = df_masuk[df_masuk['Tahun'] == thn_lap]
        
        # TABEL KAS
        st.markdown("#### 🟢 Laporan Kas (15.000)")
        if not df_yr.empty:
            rk_k = df_yr.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            st.dataframe(rk_k.reindex(columns=[b for b in bln_order if b in rk_k.columns]), use_container_width=True)
        
        # TABEL HADIAH
        st.markdown("#### 🟡 Laporan Hadiah (35.000)")
        if not df_yr.empty:
            rk_h = df_yr.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            st.dataframe(rk_h.reindex(columns=[b for b in bln_order if b in rk_h.columns]), use_container_width=True)

elif menu == "📥 Kas Bulanan":
    st.subheader("📥 Input Kas Bulanan")
    with st.form("f_kas"):
        c1, c2 = st.columns(2)
        with c1:
            nama_s = st.selectbox("Warga", sorted(df_warga['Nama'].tolist()))
            nom = st.number_input("Nominal Bayar", min_value=0, step=5000)
        with c2:
            th_s = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
            bl_s = st.selectbox("Bulan", bln_order)
        if st.form_submit_button("Simpan"):
            p_k = min(nom, 15000)
            p_h = nom - p_k
            new_k = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y"), 'Nama': nama_s, 'Tahun': th_s, 'Bulan': bl_s, 'Total': nom, 'Kas': p_k, 'Hadiah': p_h, 'Status': 'LUNAS'}])
            append_to_cloud("Pemasukan", new_k)
            st.success("Tersimpan!")
            st.rerun()

elif menu == "🎭 Event & Iuran":
    st.subheader("🎭 Iuran Event")
    with st.form("f_ev"):
        ev_n = st.text_input("Nama Event")
        w_n = st.selectbox("Nama Warga", sorted(df_warga['Nama'].tolist()))
        nom_e = st.number_input("Nominal", min_value=0)
        if st.form_submit_button("Simpan Event"):
            new_e = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y"), 'Nama': w_n, 'Nama Event': ev_n, 'Jumlah': nom_e}])
            append_to_cloud("Event", new_e)
            st.success("Iuran Event Tersimpan!")
            st.rerun()

elif menu == "📤 Pengeluaran":
    st.subheader("📤 Catat Pengeluaran")
    with st.form("f_out"):
        kat_o = st.selectbox("Sumber Dana", ["Kas", "Hadiah", "Event"])
        jml_o = st.number_input("Nominal", min_value=0)
        ket_o = st.text_input("Keterangan")
        if st.form_submit_button("Simpan Pengeluaran"):
            new_o = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y"), 'Kategori': kat_o, 'Jumlah': jml_o, 'Keterangan': ket_o}])
            append_to_cloud("Pengeluaran", new_o)
            st.success("Pengeluaran Dicatat!")
            st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("👥 Database Warga")
    with st.form("f_w"):
        nw = st.text_input("Nama Baru")
        if st.form_submit_button("Tambah Warga"):
            append_to_cloud("Warga", pd.DataFrame([{'Nama': nw, 'Role': 'Main Warga'}]))
            st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("📜 Log Transaksi")
    st.write("20 Transaksi Pemasukan Terakhir:")
    st.dataframe(df_masuk.tail(20), use_container_width=True)
