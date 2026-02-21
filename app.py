import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIG HALAMAN ---
st.set_page_config(
    page_title="AR-ROYHAAN 3 KAS MANAGEMENT",
    page_icon="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png",
    layout="wide"
)

# --- 2. CSS GLOBAL & DASHBOARD ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    
    /* Background Premium Marble */
    .stApp {
        background-color: #f8f9fa;
        background-image: url("https://www.transparenttextures.com/patterns/white-marble.png");
        background-attachment: fixed;
    }

    /* Metric Dashboard Styling */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #D4AF37;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.02);
    }
    
    /* Styling Tabel Dashboard */
    .stDataFrame {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
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
        .main-login-container {
            max-width: 420px;
            margin: auto;
            padding-top: 50px;
        }
        .header-box {
            background: #ffffff;
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            border: 2px solid #D4AF37;
            outline: 3px solid white; 
            box-shadow: 0 0 0 4px #D4AF37, 0 10px 25px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        .header-top-content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        }
        .header-logo { width: 80px; }
        .header-text-container {
            text-align: left;
            border-left: 1.5px solid #eaeaea;
            padding-left: 12px;
        }
        .header-title {
            color: #1a1a1a;
            font-size: 18px;
            font-weight: 800;
            margin: 0;
            line-height: 1;
        }
        .header-subtitle {
            color: #B8860B;
            font-size: 8px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .slogan-text {
            color: #B8860B;
            font-size: 11px;
            font-style: italic;
            font-weight: 600;
            margin-top: 8px;
            border-top: 1px solid #f8f8f8;
            padding-top: 5px;
        }
        .login-card {
            background: rgba(255, 255, 255, 0.98);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.04);
            border: 1px solid #f1f5f9;
        }
        .stTextInput label {
            color: #475569 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }
        div.stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            border: none !important;
            padding: 10px !important;
            width: 100%;
            transition: 0.3s ease;
        }
        div.stButton > button:hover {
            filter: brightness(1.1);
            transform: translateY(-1px);
        }
        </style>
    """, unsafe_allow_html=True)

    _, col_mid, _ = st.columns([0.1, 1, 0.1])
    
    with col_mid:
        st.markdown('<div class="main-login-container">', unsafe_allow_html=True)
        
        # --- HEADER BOX ---
        st.markdown(f"""
            <div class="header-box">
                <div class="header-top-content">
                    <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" class="header-logo">
                    <div class="header-text-container">
                        <p class="header-title">AR-ROYHAAN 3</p>
                        <p class="header-subtitle">KAS MANAGEMENT</p>
                    </div>
                </div>
                <div class="slogan-text">"We Came to Learn and bring science back"</div>
            </div>
        """, unsafe_allow_html=True)
        
        # --- FORM LOGIN ---
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            st.markdown("<p style='text-align:center; color:#94a3b8; font-size:12px; margin-bottom:15px;'>Silakan masuk dengan kredensial anda</p>", unsafe_allow_html=True)
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

# Eksekusi Login Proteksi
if not st.session_state['logged_in']:
    login()
    st.stop()

# --- 4. SISTEM DATA & FUNGSI (Hanya jalan setelah login) ---

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

# Load Initial Data
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- 5. SIDEBAR ---
def logout():
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown(f"### 👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🚪 Logout"):
    logout()

if st.session_state['role'] == "admin":
    list_menu = ["📊 Laporan", "📥 Pemasukan", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"]
else:
    list_menu = ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Navigasi Utama", list_menu)

# --- 6. HEADER DASHBOARD ---
st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
        <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="55">
        <div>
            <h2 style="margin:0; color:#1e293b;">AR-ROYHAAN 3</h2>
            <p style="margin:0; color:#B8860B; font-weight:600; font-size:12px;">DASHBOARD MANAJEMEN KEUANGAN</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Metrik
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()

c1, c2, c3 = st.columns(3)
c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
c3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")
st.divider()

# --- 7. LOGIKA MENU ---
if menu == "📊 Laporan":
    st.subheader("📋 Laporan Tahunan")
    thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
    t1, t2 = st.tabs(["📥 Pemasukan", "📤 Pengeluaran"])
    
    with t1:
        df_yr = df_masuk[df_masuk['Tahun'] == thn_lap]
        if not df_yr.empty:
            bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            st.write("### 💰 Dana KAS")
            rkp_k = df_yr.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            rkp_k = rkp_k.reindex(columns=[b for b in bln_order if b in rkp_k.columns])
            st.dataframe(rkp_k.style.format("{:,.0f}"), use_container_width=True)
            
            st.write("### 🎁 Dana HADIAH")
            rkp_h = df_yr.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            rkp_h = rkp_h.reindex(columns=[b for b in bln_order if b in rkp_h.columns])
            st.dataframe(rkp_h.style.format("{:,.0f}"), use_container_width=True)

elif menu == "📥 Pemasukan":
    st.subheader("Input Pembayaran Baru")
    nama_p = st.selectbox("Pilih Anggota", sorted(df_warga['Nama'].tolist()))
    role_p = df_warga.loc[df_warga['Nama'] == nama_p, 'Role'].values[0]
    with st.form("in_form", clear_on_submit=True):
        st.info(f"Anggota: {nama_p} ({role_p})")
        nom = st.number_input("Nominal Pembayaran (Rp)", min_value=0, step=5000)
        thn = st.selectbox("Tahun Mulai", list(range(2022, 2031)), index=4)
        bln = st.selectbox("Bulan Mulai", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        tp = st.selectbox("Alokasi", ["Paket Lengkap"] if role_p == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
        
        if st.form_submit_button("✅ Simpan Data"):
            if nom > 0:
                res = proses_bayar(nama_p, nom, thn, bln, tp, role_p, df_masuk)
                df_updated = pd.concat([df_masuk, res], ignore_index=True)
                save_to_cloud("Pemasukan", df_updated)
                st.success("Pembayaran berhasil dicatat!")
                st.rerun()

elif menu == "📤 Pengeluaran":
    st.subheader("Catat Pengeluaran Dana")
    with st.form("out_form"):
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah"])
        jml = st.number_input("Nominal (Rp)", min_value=0)
        ket = st.text_input("Keterangan Penggunaan")
        if st.form_submit_button("Simpan Pengeluaran"):
            if jml > 0 and ket:
                new_o = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat, 'Jumlah': jml, 'Keterangan': ket}])
                df_updated = pd.concat([df_keluar, new_o], ignore_index=True)
                save_to_cloud("Pengeluaran", df_updated)
                st.success("Pengeluaran berhasil dicatat!")
                st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("Manajemen Anggota")
    t1, t2 = st.tabs(["➕ Tambah", "🗑️ Hapus"])
    with t1:
        with st.form("add_w"):
            nw = st.text_input("Nama Lengkap")
            rl = st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Tambah"):
                if nw:
                    new_df = pd.concat([df_warga, pd.DataFrame([{'Nama':nw, 'Role':rl}])], ignore_index=True)
                    save_to_cloud("Warga", new_df)
                    st.rerun()
    with t2:
        target = st.selectbox("Pilih Nama yang Dihapus", df_warga['Nama'].tolist())
        if st.button("Hapus Permanen", type="primary"):
            new_df = df_warga[df_warga['Nama'] != target]
            save_to_cloud("Warga", new_df)
            st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("Histori Transaksi")
    st.write("### Pemasukan")
    st.dataframe(df_masuk.sort_index(ascending=False), use_container_width=True)
    st.write("### Pengeluaran")
    st.dataframe(df_keluar.sort_index(ascending=False), use_container_width=True)
