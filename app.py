import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIG HALAMAN ---
st.set_page_config(
    page_title="AR3 Keuangan",
    page_icon="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png",
    layout="wide"
)

# --- MAGIC CODE UNTUK IKON HP (PWA) ---
st.markdown(
    """
    <head>
        <link rel="apple-touch-icon" href="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png">
        <link rel="icon" href="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black">
    </head>
    """,
    unsafe_allow_html=True
)

# --- SISTEM LOGIN SEDERHANA ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

def login():
    st.sidebar.title("🔐 Login Sistem")
    with st.sidebar.form("login_form"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if user == "admin" and pwd == "admin123":
                st.session_state['logged_in'] = True
                st.session_state['role'] = "admin"
                st.rerun()
            elif user == "warga" and pwd == "warga123":
                st.session_state['logged_in'] = True
                st.session_state['role'] = "user"
                st.rerun()
            else:
                st.error("Username/Password Salah")

def logout():
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.rerun()

if not st.session_state['logged_in']:
    login()
    st.warning("Silakan login untuk mengakses data.")
    st.stop()

# --- JIKA SUDAH LOGIN ---
st.sidebar.success(f"Login sebagai: {st.session_state['role'].upper()}")
if st.sidebar.button("Logout"):
    logout()

if st.session_state['role'] == "admin":
    list_menu = ["📊 Laporan & Monitoring", "📥 Input Pemasukan", "📤 Input Pengeluaran", "👥 Kelola Warga", "📜 Log Transaksi"]
else:
    list_menu = ["📊 Laporan & Monitoring", "📜 Log Transaksi"]

menu = st.sidebar.radio("Navigasi", list_menu)

# --- KONEKSI GSPREAD ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gspread_credentials"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

SHEET_ID = "1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE"
sh = client.open_by_key(SHEET_ID)

def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    numeric_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def save_to_cloud(sheet_name, df):
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

def proses_bayar(nama, nominal, thn, bln, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx_bln = list_bulan.index(bln)
    sisa = nominal
    data_baru = []
    while sisa > 0:
        curr_bln = list_bulan[idx_bln]
        if role == "Main Warga":
            kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == curr_bln) & (df_existing['Tahun'] == thn)
            sdh_bayar = df_existing[kondisi]['Total'].sum()
            sdh_kas = df_existing[kondisi]['Kas'].sum()
            if sdh_bayar < 50000:
                butuh = 50000 - sdh_bayar
                bayar_ini = min(sisa, butuh)
                p_kas = min(bayar_ini, max(0, 15000 - sdh_kas))
                p_hadiah = bayar_ini - p_kas
                data_baru.append({
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Nama': nama, 'Tahun': thn, 'Bulan': curr_bln,
                    'Total': bayar_ini, 'Kas': p_kas, 'Hadiah': p_hadiah,
                    'Status': "LUNAS" if (sdh_bayar + bayar_ini) >= 50000 else "CICIL",
                    'Tipe': "Paket Lengkap"
                })
                sisa -= bayar_ini
        else:
            data_baru.append({
                'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'Nama': nama, 'Tahun': thn, 'Bulan': curr_bln,
                'Total': sisa, 'Kas': sisa if tipe == "Hanya Kas" else 0,
                'Hadiah': sisa if tipe == "Hanya Hadiah" else 0,
                'Status': "SUPPORT", 'Tipe': tipe
            })
            sisa = 0
        idx_bln += 1
        if idx_bln > 11: 
            idx_bln = 0
            thn += 1
        if thn > 2030: break
    return pd.DataFrame(data_baru)

# --- LOAD DATA ---
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- CSS CUSTOM UNTUK TAMPILAN PREMIUM ---
st.markdown("""
    <style>
    .header-container {
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 10px 0;
    }
    .logo-img { width: 70px; }
    .title-text { margin: 0; font-size: 28px; font-weight: 700; color: #31333F; }
    @media (max-width: 640px) {
        .title-text { font-size: 20px; }
        .logo-img { width: 50px; }
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f1f1 100%);
        border: 1px solid #D4AF37;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"] {
        color: #D4AF37 !important;
        font-weight: bold !important;
    }
    </style>
    <div class="header-container">
        <img class="logo-img" src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png">
        <h1 class="title-text">Dashboard Keuangan AR3</h1>
    </div>
""", unsafe_allow_html=True)

st.divider()

# --- DASHBOARD METRIK ---
_, col_main, _ = st.columns([0.1, 4, 0.1]) 
with col_main:
    in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
    out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
    out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
    with c2: st.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
    with c3: st.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")

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
            
            st.divider()
            st.write("### 👤 Ringkasan Total Kontribusi")
            ringkasan = df_yr_in.groupby('Nama').agg({'Kas':'sum','Hadiah':'sum','Total':'sum'})
            st.table(ringkasan.style.format("{:,.0f}"))
        else:
            st.info("Belum ada data pemasukan tahun ini.")

    with tab2:
        df_keluar['Tahun_Log'] = df_keluar['Tanggal'].str.split('/').str[2].str.split(' ').str[0]
        df_yr_out = df_keluar[df_keluar['Tahun_Log'] == str(thn_lap)]
        if not df_yr_out.empty:
            st.dataframe(df_yr_out[['Tanggal', 'Kategori', 'Jumlah', 'Keterangan']], use_container_width=True)
        else:
            st.info("Tidak ada data pengeluaran tahun ini.")

elif menu == "📥 Input Pemasukan":
    st.subheader("Input Pembayaran")
    nama_p = st.selectbox("Pilih Nama", sorted(df_warga['Nama'].tolist()))
    role_p = df_warga.loc[df_warga['Nama'] == nama_p, 'Role'].values[0]
    with st.form("in_form", clear_on_submit=True):
        st.write(f"Status: **{role_p}**")
        nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        tipe = st.selectbox("Alokasi", ["Paket Lengkap"] if role_p == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
        thn = st.selectbox("Tahun Mulai", list(range(2022, 2031)), index=4)
        bln = st.selectbox("Bulan Mulai", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
