import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIG HALAMAN ---
st.set_page_config(
    page_title="AR3 Keuangan",
    page_icon="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png",
    layout="wide"
)

# --- 2. CSS GLOBAL (Polesan Final agar Fit & Simetris) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    
    /* Background Premium Marble */
    .stApp {
        background-color: #f8f9fa;
        background-image: url("https://www.transparenttextures.com/patterns/white-marble.png");
        background-attachment: fixed;
    }

    /* Container Login agar Fit */
    .main-login-container {
        max-width: 420px;
        margin: auto;
        padding-top: 50px;
    }

    /* Header Box Emas */
    .header-box {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 2px solid #D4AF37;
        outline: 3px solid white; 
        box-shadow: 0 0 0 4px #D4AF37, 0 15px 30px rgba(0,0,0,0.08);
        margin-bottom: 25px; 
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
    }

    .header-logo { width: 55px; }

    .header-text-container {
        text-align: left;
        border-left: 2px solid #eaeaea;
        padding-left: 15px;
    }

    .header-title {
        color: #1a1a1a;
        font-family: 'Inter', sans-serif;
        font-size: 20px;
        font-weight: 800;
        margin: 0;
        line-height: 1.1;
    }

    .header-subtitle {
        color: #B8860B;
        font-size: 9px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Card Login */
    .login-card {
        background: white;
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.05);
        border: 1px solid #f1f5f9;
    }

    /* Tombol Masuk Emas */
    div.stButton > button {
        background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
        color: white !important;
        border-radius: 10px !important;
        width: 100%;
        font-weight: 700 !important;
        border: none !important;
        padding: 10px !important;
    }

    /* Metric Dashboard */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #D4AF37;
        padding: 15px;
        border-radius: 12px;
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
        st.markdown('<div class="main-login-container">', unsafe_allow_html=True)
        # Header Box
        st.markdown(f"""
            <div class="header-box">
                <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" class="header-logo">
                <div class="header-text-container">
                    <p class="header-title">AR-ROYHAAN</p>
                    <p class="header-subtitle">Management System</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Form Login
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            st.markdown("<p style='text-align:center; color:#64748b; font-size:14px;'>Silakan masuk dengan akun anda</p>", unsafe_allow_html=True)
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk Ke Aplikasi")
            
            if submit:
                if "users" in st.secrets:
                    u_data = st.secrets["users"]
                    if user == u_data.get("admin_user") and pwd == u_data.get("admin_password"):
                        st.session_state.update({"logged_in": True, "role": "admin"})
                        st.rerun()
                    elif user == u_data.get("warga_user") and pwd == u_data.get("warga_password"):
                        st.session_state.update({"logged_in": True, "role": "user"})
                        st.rerun()
                    else:
                        st.error("Username atau Password salah.")
        st.markdown('</div></div>', unsafe_allow_html=True)

# Proteksi Halaman
if not st.session_state['logged_in']:
    login()
    st.stop() # Berhenti di sini kalau belum login, jadi dashboard gak ngintip

# --- 4. HALAMAN DASHBOARD (Hanya muncul kalau sudah login) ---

# Fungsi-fungsi Data
def logout():
    st.session_state.clear()
    st.rerun()

# Sidebar
st.sidebar.success(f"Login: {st.session_state['role'].upper()}")
if st.sidebar.button("Logout"):
    logout()

# Filter Menu
if st.session_state['role'] == "admin":
    list_menu = ["📊 Laporan & Monitoring", "📥 Input Pemasukan", "📤 Input Pengeluaran", "👥 Kelola Warga", "📜 Log Transaksi"]
else:
    list_menu = ["📊 Laporan & Monitoring", "📜 Log Transaksi"]
menu = st.sidebar.radio("Navigasi", list_menu)

# Koneksi GSpread
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    df = pd.DataFrame(worksheet.get_all_records())
    numeric_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def save_to_cloud(sheet_name, df):
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# Load Data
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- HEADER DASHBOARD (Baru muncul setelah Login) ---
st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
        <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="50">
        <h2 style="margin:0;">Dashboard Keuangan AR3</h2>
    </div>
""", unsafe_allow_html=True)

# Metrik Utama
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()

c1, c2, c3 = st.columns(3)
c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
c3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")
st.divider()

# --- LOGIKA MENU ---
if menu == "📊 Laporan & Monitoring":
    st.subheader("📋 Laporan Keuangan Tahunan")
    thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
    tab1, tab2 = st.tabs(["📥 Pemasukan", "📤 Pengeluaran"])
    
    with tab1:
        df_yr_in = df_masuk[df_masuk['Tahun'] == thn_lap]
        if not df_yr_in.empty:
            bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            st.write("### 💰 Laporan Dana KAS (Rp 15.000/bln)")
            rekap_kas = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            rekap_kas = rekap_kas.reindex(columns=[b for b in bln_order if b in rekap_kas.columns])
            st.dataframe(rekap_kas.style.highlight_between(left=15000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
            
            st.divider()
            st.write("### 🎁 Laporan Dana HADIAH (Rp 35.000/bln)")
            rekap_hadiah = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            rekap_hadiah = rekap_hadiah.reindex(columns=[b for b in bln_order if b in rekap_hadiah.columns])
            st.dataframe(rekap_hadiah.style.highlight_between(left=35000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
        else:
            st.info("Belum ada data pemasukan tahun ini.")

elif menu == "📥 Input Pemasukan":
    st.subheader("Input Pembayaran")
    nama_p = st.selectbox("Pilih Nama", sorted(df_warga['Nama'].tolist()))
    role_p = df_warga.loc[df_warga['Nama'] == nama_p, 'Role'].values[0]
    with st.form("in_form", clear_on_submit=True):
        st.write(f"Status: **{role_p}**")
        nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        tipe = st.selectbox("Alokasi", ["Paket Lengkap"] if role_p == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
        thn = st.selectbox("Tahun Mulai", list(range(2022, 2031)), index=4)
        bln = st.selectbox("Bulan Mulai", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        if st.form_submit_button("Simpan Pembayaran"):
            res = proses_bayar(nama_p, nom, thn, bln, tipe, role_p, df_masuk)
            if not res.empty:
                df_updated = pd.concat([df_masuk, res], ignore_index=True)
                save_to_cloud("Pemasukan", df_updated)
                st.success("Pembayaran Berhasil Disimpan!")
                st.rerun()

elif menu == "📤 Input Pengeluaran":
    st.subheader("Catat Pengeluaran")
    with st.form("out_form", clear_on_submit=True):
        kat = st.radio("Ambil Dana Dari", ["Kas", "Hadiah"])
        nom = st.number_input("Nominal Pengeluaran", min_value=0)
        ket = st.text_input("Keperluan / Keterangan")
        if st.form_submit_button("Simpan"):
            if nom > 0 and ket:
                new_o = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat, 'Jumlah': nom, 'Keterangan': ket}])
                df_updated = pd.concat([df_keluar, new_o], ignore_index=True)
                save_to_cloud("Pengeluaran", df_updated)
                st.success("Tersimpan!")
                st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("Manajemen Anggota")
    tab_t, tab_e = st.tabs(["➕ Tambah", "⚙️ Edit / Hapus"])
    with tab_t:
        with st.form("add_form", clear_on_submit=True):
            n_br = st.text_input("Nama Lengkap")
            r_br = st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Simpan"):
                if n_br:
                    new_w = pd.concat([df_warga, pd.DataFrame([{'Nama':n_br, 'Role':r_br}])], ignore_index=True)
                    save_to_cloud("Warga", new_w)
                    st.rerun()
    with tab_e:
        if not df_warga.empty:
            target = st.selectbox("Pilih Warga", df_warga['Nama'].tolist())
            if st.button("🗑️ Hapus Warga", type="primary"):
                new_w = df_warga[df_warga['Nama'] != target]
                save_to_cloud("Warga", new_w)
                st.rerun()
    st.table(df_warga)

elif menu == "📜 Log Transaksi":
    st.subheader("Semua Histori Transaksi")
    st.write("### Pemasukan")
    st.dataframe(df_masuk.sort_index(ascending=False), use_container_width=True)
    st.write("### Pengeluaran")
    st.dataframe(df_keluar.sort_index(ascending=False), use_container_width=True)
