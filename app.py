import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import io

# --- 1. CONFIG HALAMAN ---
st.set_page_config(
    page_title="AR-ROYHAAN 3 KAS MANAGEMENT",
    page_icon="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png",
    layout="wide"
)

# --- 2. CSS GLOBAL ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp {
        background-color: #f8f9fa;
        background-image: url("https://www.transparenttextures.com/patterns/white-marble.png");
        background-attachment: fixed;
    }
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
    st.markdown("""<style>.main-login-container { max-width: 420px; margin: auto; padding-top: 50px; }</style>""", unsafe_allow_html=True)
    _, col_mid, _ = st.columns([0.1, 1, 0.1])
    with col_mid:
        st.markdown(f"""
            <div style="text-align: center; border: 2px solid #D4AF37; padding: 20px; border-radius: 15px; background: white;">
                <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="80">
                <h3>AR-ROYHAAN 3</h3>
                <p>KAS MANAGEMENT</p>
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
                else: st.error("Login Gagal")

if not st.session_state['logged_in']:
    login()
    st.stop()

# --- 4. LOGIKA DATA (DENGAN CACHE AGAR TIDAK QUOTA EXCEEDED) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

# Cache data selama 10 menit untuk mengurangi read requests
@st.cache_data(ttl=600)
def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    if not data:
        cols = {
            "Pemasukan": ['Tanggal', 'Nama', 'Tahun', 'Bulan', 'Total', 'Kas', 'Hadiah', 'Status', 'Tipe'],
            "Pengeluaran": ['Tanggal', 'Kategori', 'Jumlah', 'Keterangan'],
            "Warga": ['Nama', 'Role']
        }
        return pd.DataFrame(columns=cols.get(sheet_name, []))
    df = pd.DataFrame(data)
    num_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for c in num_cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

def clear_cache_and_rerun():
    st.cache_data.clear()
    st.rerun()

# --- 5. SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🔄 Refresh Data"):
    clear_cache_and_rerun()
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

list_menu = ["📊 Laporan", "📥 Pemasukan", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Menu", list_menu)

# Load Data
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- 6. DASHBOARD ---
in_k = df_masuk['Kas'].sum() if 'Kas' in df_masuk.columns else 0
in_h = df_masuk['Hadiah'].sum() if 'Hadiah' in df_masuk.columns else 0
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum() if not df_keluar.empty else 0
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum() if not df_keluar.empty else 0

st.title("AR-ROYHAAN 3 DASHBOARD")
m1, m2, m3 = st.columns(3)
m1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
m3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")

# --- 7. MENU LOGIC ---
if menu == "📊 Laporan":
    thn = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
    df_yr_in = df_masuk[df_masuk['Tahun'] == thn]
    
    t1, t2, t3 = st.tabs(["📥 Masuk", "📤 Keluar", "🏆 Rekap"])
    with t1:
        if not df_yr_in.empty:
            st.write("### Dana KAS")
            st.dataframe(df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0), use_container_width=True)
        else: st.info("Kosong")
    
    with t2:
        def get_yr(d):
            try: return int(str(d).split('/')[2].split(' ')[0])
            except: return 0
        df_keluar['Y'] = df_keluar['Tanggal'].apply(get_yr)
        st.dataframe(df_keluar[df_keluar['Y'] == thn], use_container_width=True)

    with t3:
        if not df_yr_in.empty:
            rekap = df_yr_in.groupby('Nama').agg({'Total':'sum'}).reset_index()
            rekap['Status'] = rekap['Total'].apply(lambda x: "LUNAS" if x >= 600000 else "BELUM")
            st.table(rekap)

elif menu == "📥 Pemasukan":
    with st.form("in"):
        n = st.selectbox("Nama", sorted(df_warga['Nama'].tolist()))
        nom = st.number_input("Nominal", min_value=0, step=5000)
        th = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
        bl = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        if st.form_submit_button("Simpan"):
            # Proses bayar sederhana (logic as per your previous version)
            p_kas = min(nom, 15000)
            p_hadiah = nom - p_kas
            new_data = [[datetime.now().strftime("%d/%m/%Y %H:%M"), n, th, bl, nom, p_kas, p_hadiah, "BAYAR", "Paket"]]
            sh.worksheet("Pemasukan").append_rows(new_data)
            st.success("Berhasil!")
            clear_cache_and_rerun()

elif menu == "📤 Pengeluaran":
    with st.form("out"):
        kat = st.radio("Kategori", ["Kas", "Hadiah"])
        jml = st.number_input("Jumlah", min_value=0)
        ket = st.text_input("Ket")
        if st.form_submit_button("Simpan"):
            sh.worksheet("Pengeluaran").append_rows([[datetime.now().strftime("%d/%m/%Y %H:%M"), kat, jml, ket]])
            st.success("Tersimpan!")
            clear_cache_and_rerun()

elif menu == "👥 Kelola Warga":
    nw = st.text_input("Nama Baru")
    rl = st.selectbox("Role", ["Main Warga", "Warga Support"])
    if st.button("Tambah"):
        sh.worksheet("Warga").append_rows([[nw, rl]])
        clear_cache_and_rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.dataframe(df_masuk.sort_index(ascending=False), use_container_width=True)
