
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
        box-shadow: 2px 2px 10px rgba(0,0,0,0.02);
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
        div.stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
            color: white !important; width: 100%; font-weight: 700; border: none; padding: 10px; border-radius: 8px;
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
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state['logged_in']:
    login()
    st.stop()

# --- 4. LOGIKA DATA (SPREADSHEET) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    df = pd.DataFrame(worksheet.get_all_records())
    numeric_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in numeric_cols:
        if col in df.columns: 
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def append_to_cloud(sheet_name, df_new):
    """Menambah baris baru tanpa menghapus data lama (Lebih Aman)"""
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_rows(df_new.values.tolist())

def rewrite_cloud(sheet_name, df_full):
    """Hanya digunakan untuk update total (seperti hapus warga)"""
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df_full.columns.values.tolist()] + df_full.values.tolist())

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
            # Untuk Warga Support, langsung masukkan semua sisa ke satu entri
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

# Load Data Utama
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- 5. SIDEBAR ---
st.sidebar.markdown(f"### 👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

list_menu = ["📊 Laporan", "📥 Pemasukan", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Navigasi Utama", list_menu)

# --- 6. METRIK DASHBOARD ---
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()

st.markdown(f"## AR-ROYHAAN 3 DASHBOARD")
m1, m2, m3 = st.columns(3)
m1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
m3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")
st.divider()

# --- 7. LOGIKA MENU ---

if menu == "📊 Laporan":
    st.subheader("📋 Laporan Tahunan")
    thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
    tab1, tab2, tab3 = st.tabs(["📥 Pemasukan", "📤 Pengeluaran", "🏆 Ringkasan"])

    # Filter Tahun
    df_yr_in = df_masuk[df_masuk['Tahun'] == thn_lap]
    
    # Helper untuk extract tahun dari string tanggal dd/mm/yyyy
    def get_yr(d):
        try: return int(str(d).split('/')[2].split(' ')[0])
        except: return 0
    df_keluar['Thn_Cek'] = df_keluar['Tanggal'].apply(get_yr)
    df_yr_out = df_keluar[df_keluar['Thn_Cek'] == thn_lap]

    bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

    with tab1:
        if not df_yr_in.empty:
            st.write("### 💰 Dana KAS (Rp 15.000)")
            rekap_k = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            cols_k = [b for b in bln_order if b in rekap_k.columns]
            st.dataframe(rekap_k[cols_k].style.highlight_between(left=15000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
            
            st.write("### 🎁 Dana HADIAH (Rp 35.000)")
            rekap_h = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            cols_h = [b for b in bln_order if b in rekap_h.columns]
            st.dataframe(rekap_h[cols_h].style.highlight_between(left=35000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
        else: st.info("Tidak ada data.")

    with tab2:
        if not df_yr_out.empty:
            st.dataframe(df_yr_out[['Tanggal', 'Kategori', 'Jumlah', 'Keterangan']], use_container_width=True)
        else: st.info("Tidak ada pengeluaran.")

    with tab3:
        if not df_yr_in.empty:
            rekap_all = df_yr_in.groupby('Nama').agg({'Kas':'sum','Hadiah':'sum','Total':'sum'}).reset_index()
            rekap_all['Status'] = rekap_all['Total'].apply(lambda x: "✅ LUNAS" if x >= 600000 else f"⚠️ -Rp {600000-x:,.0f}")
            st.table(rekap_all.style.format({"Kas": "{:,.0f}", "Hadiah": "{:,.0f}", "Total": "{:,.0f}"}))

elif menu == "📥 Pemasukan":
    st.subheader("📥 Input Pembayaran")
    nama_sel = st.selectbox("Pilih Anggota", sorted(df_warga['Nama'].tolist()))
    role_sel = df_warga.loc[df_warga['Nama'] == nama_sel, 'Role'].values[0]
    
    with st.form("form_in", clear_on_submit=True):
        st.info(f"Role: {role_sel}")
        nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        tp = st.selectbox("Alokasi", ["Paket Lengkap"] if role_sel == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
        th = st.selectbox("Mulai Tahun", list(range(2022, 2031)), index=4)
        bl = st.selectbox("Mulai Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        
        if st.form_submit_button("Simpan Pembayaran"):
            if nom > 0:
                res_df = proses_bayar(nama_sel, nom, th, bl, tp, role_sel, df_masuk)
                append_to_cloud("Pemasukan", res_df)
                st.success("Data Berhasil Ditambahkan!")
                st.rerun()

elif menu == "📤 Pengeluaran":
    st.subheader("📤 Catat Pengeluaran")
    with st.form("form_out", clear_on_submit=True):
        kat_out = st.radio("Sumber Dana", ["Kas", "Hadiah"])
        jml_out = st.number_input("Jumlah (Rp)", min_value=0)
        ket_out = st.text_input("Keterangan")
        if st.form_submit_button("Simpan Pengeluaran"):
            if jml_out > 0:
                new_out_df = pd.DataFrame([{
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Kategori': kat_out, 'Jumlah': jml_out, 'Keterangan': ket_out
                }])
                append_to_cloud("Pengeluaran", new_out_df)
                st.success("Pengeluaran Tercatat!")
                st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("👥 Kelola Anggota")
    t1, t2 = st.tabs(["➕ Tambah", "🗑️ Hapus"])
    
    with t1:
        with st.form("f_add", clear_on_submit=True):
            n_baru = st.text_input("Nama Lengkap")
            r_baru = st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Tambah Anggota"):
                if n_baru and n_baru not in df_warga['Nama'].values:
                    # Kita pakai rewrite karena data warga biasanya sedikit dan perlu struktur kolom yang bersih
                    updated_w = pd.concat([df_warga, pd.DataFrame([{'Nama': n_baru, 'Role': r_baru}])], ignore_index=True)
                    rewrite_cloud("Warga", updated_w)
                    st.success("Anggota Ditambahkan!")
                    st.rerun()
                else: st.error("Nama tidak valid atau sudah ada.")
                
    with t2:
        if not df_warga.empty:
            n_del = st.selectbox("Pilih Nama yang Dihapus", sorted(df_warga['Nama'].tolist()))
            if st.button("Hapus Permanen"):
                updated_w = df_warga[df_warga['Nama'] != n_del]
                rewrite_cloud("Warga", updated_w)
                st.success("Anggota Dihapus!")
                st.rerun()

    st.write("### 📜 Daftar Warga")
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("📜 Log Transaksi Pemasukan")
    st.dataframe(df_masuk.sort_index(ascending=False), use_container_width=True)
