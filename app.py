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
    st.markdown("""
        <style>
        .main-login-container { max-width: 420px; margin: auto; padding-top: 50px; }
        .header-box {
            background: #ffffff; border-radius: 12px; padding: 12px; text-align: center;
            border: 2px solid #D4AF37; outline: 3px solid white; 
            box-shadow: 0 0 0 4px #D4AF37, 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 20px;
        }
        .header-logo { width: 50px; }
        .header-title { color: #1a1a1a; font-size: 18px; font-weight: 800; margin: 0; }
        .header-subtitle { color: #B8860B; font-size: 8px; font-weight: 700; letter-spacing: 1px; }
        .slogan-text { color: #B8860B; font-size: 11px; font-style: italic; font-weight: 600; margin-top: 8px; }
        .login-card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 8px 30px rgba(0,0,0,0.04); }
        div.stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
            color: white !important; width: 100%; font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)

    _, col_mid, _ = st.columns([0.1, 1, 0.1])
    with col_mid:
        st.markdown('<div class="main-login-container">', unsafe_allow_html=True)
        st.markdown(f"""
            <div class="header-box">
                <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" class="header-logo">
                <p class="header-title">AR-ROYHAAN 3</p>
                <p class="header-subtitle">KAS MANAGEMENT</p>
                <div class="slogan-text">"We Came to Learn and bring science back"</div>
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
                else:
                    st.error("Gagal Login.")
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state['logged_in']:
    login()
    st.stop()

# --- 4. DATA SPREADSHEET ---
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

# Load Data Utama
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- 5. SIDEBAR ---
st.sidebar.markdown(f"### 👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

if st.session_state['role'] == "admin":
    list_menu = ["📊 Laporan", "📥 Pemasukan", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"]
else:
    list_menu = ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Navigasi Utama", list_menu)

# --- 6. METRIK DASHBOARD ---
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()

st.markdown(f"## AR-ROYHAAN 3 DASHBOARD")
c1, c2, c3 = st.columns(3)
c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
c3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")
st.divider()

# --- 7. LOGIKA MENU ---
if menu == "📊 Laporan":
    st.subheader("📋 Monitoring Keuangan")
    thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
    tab_ringkasan, tab_pemasukan, tab_pengeluaran = st.tabs(["🏆 Ringkasan", "📥 Masuk", "📤 Keluar"])
    
    df_yr_in = df_masuk[df_masuk['Tahun'] == thn_lap]
    
    with tab_ringkasan:
        st.write(f"### Status Pembayaran {thn_lap}")
        if not df_yr_in.empty:
            status_warga = df_yr_in.groupby('Nama').agg({'Kas':'sum','Hadiah':'sum','Total':'sum'}).reset_index()
            status_warga['Status'] = status_warga['Total'].apply(lambda x: "✅ LUNAS" if x >= 600000 else f"⚠️ -Rp {600000-x:,.0f}")
            st.dataframe(status_warga.style.format({"Kas": "{:,.0f}", "Hadiah": "{:,.0f}", "Total": "{:,.0f}"}), use_container_width=True)
            
            # Button Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                status_warga.to_excel(writer, index=False, sheet_name='Ringkasan')
            st.download_button(label="📊 Download Excel", data=output.getvalue(), file_name=f'Kas_{thn_lap}.xlsx')
        else:
            st.warning("Belum ada data.")

    with tab_pemasukan:
        if not df_yr_in.empty:
            bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            st.write("### Detail Kas")
            rkp_k = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            st.dataframe(rkp_k.reindex(columns=[b for b in bln_order if b in rkp_k.columns]).style.format("{:,.0f}"))
        else:
            st.info("Data Kosong")

    with tab_pengeluaran:
        df_keluar['Tahun_Keluar'] = pd.to_datetime(df_keluar['Tanggal'], dayfirst=True).dt.year
        df_yr_out = df_keluar[df_keluar['Tahun_Keluar'] == thn_lap]
        st.table(df_yr_out)

elif menu == "📥 Pemasukan":
    st.subheader("Input Pembayaran")
    with st.form("in_form", clear_on_submit=True):
        nama_p = st.selectbox("Nama", sorted(df_warga['Nama'].tolist()))
        nom = st.number_input("Nominal", min_value=0, step=5000)
        thn = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
        bln = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        if st.form_submit_button("Simpan"):
            # Proses sederhana (Kas 15rb, sisanya Hadiah)
            p_kas = min(nom, 15000)
            p_hadiah = nom - p_kas
            new_data = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Nama': nama_p, 'Tahun': thn, 'Bulan': bln, 'Total': nom, 'Kas': p_kas, 'Hadiah': p_hadiah, 'Status': 'BAYAR'}])
            save_to_cloud("Pemasukan", pd.concat([df_masuk, new_data], ignore_index=True))
            st.success("Berhasil!")
            st.rerun()

elif menu == "📤 Pengeluaran":
    st.subheader("Catat Pengeluaran")
    with st.form("out_form"):
        kat = st.radio("Kategori", ["Kas", "Hadiah"])
        jml = st.number_input("Jumlah", min_value=0)
        ket = st.text_input("Keterangan")
        if st.form_submit_button("Simpan"):
            new_o = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat, 'Jumlah': jml, 'Keterangan': ket}])
            save_to_cloud("Pengeluaran", pd.concat([df_keluar, new_o], ignore_index=True))
            st.success("Tercatat!")
            st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("Manajemen Warga")
    with st.form("add_w"):
        nw = st.text_input("Nama Baru")
        if st.form_submit_button("Tambah"):
            save_to_cloud("Warga", pd.concat([df_warga, pd.DataFrame([{'Nama':nw, 'Role':'Main Warga'}])], ignore_index=True))
            st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.write("### Log Transaksi")
    st.dataframe(df_masuk.sort_index(ascending=False))
