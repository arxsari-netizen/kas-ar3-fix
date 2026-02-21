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
        .login-card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 8px 30px rgba(0,0,0,0.04); }
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

# --- 4. LOGIKA DATA & PROSES ---
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

# Load Data Awal
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
    st.subheader("📋 Laporan Keuangan Tahunan")
    thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
    tab1, tab2, tab3 = st.tabs(["📥 Pemasukan", "📤 Pengeluaran", "🏆 Ringkasan"])

    df_yr_in = df_masuk[df_masuk['Tahun'] == thn_lap]
    bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

    with tab1:
        if not df_yr_in.empty:
            st.write("### 💰 Dana KAS (Rp 15.000/bln)")
            rekap_kas = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            rekap_kas = rekap_kas.reindex(columns=[b for b in bln_order if b in rekap_kas.columns])
            st.dataframe(rekap_kas.style.highlight_between(left=15000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
            
            st.write("### 🎁 Dana HADIAH (Rp 35.000/bln)")
            rekap_hadiah = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            rekap_hadiah = rekap_hadiah.reindex(columns=[b for b in bln_order if b in rekap_hadiah.columns])
            st.dataframe(rekap_hadiah.style.highlight_between(left=35000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
        else:
            st.info("Data kosong.")

    with tab2:
        df_keluar['Tahun_Log'] = pd.to_datetime(df_keluar['Tanggal'], dayfirst=True, errors='coerce').dt.year
        df_yr_out = df_keluar[df_keluar['Tahun_Log'] == thn_lap]
        if not df_yr_out.empty:
            st.dataframe(df_yr_out[['Tanggal', 'Kategori', 'Jumlah', 'Keterangan']], use_container_width=True)
        else:
            st.info("Tidak ada pengeluaran.")

    with tab3:
        if not df_yr_in.empty:
            ringkasan = df_yr_in.groupby('Nama').agg({'Kas':'sum','Hadiah':'sum','Total':'sum'}).reset_index()
            ringkasan['Status'] = ringkasan['Total'].apply(lambda x: "✅ LUNAS" if x >= 600000 else f"⚠️ -Rp {600000-x:,.0f}")
            st.dataframe(ringkasan.style.format({"Kas": "{:,.0f}", "Hadiah": "{:,.0f}", "Total": "{:,.0f}"}), use_container_width=True)
            
            # Excel Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                ringkasan.to_excel(writer, index=False, sheet_name='Ringkasan')
            st.download_button(label="📥 Download Excel", data=output.getvalue(), file_name=f'Laporan_{thn_lap}.xlsx')

elif menu == "📥 Pemasukan":
    st.subheader("Input Pembayaran Baru")
    nama_p = st.selectbox("Pilih Anggota", sorted(df_warga['Nama'].tolist()))
    role_p = df_warga.loc[df_warga['Nama'] == nama_p, 'Role'].values[0]
    with st.form("in_form", clear_on_submit=True):
        st.info(f"Anggota: {nama_p} ({role_p})")
        nom = st.number_input("Nominal Pembayaran (Rp)", min_value=0, step=5000)
        tp = st.selectbox("Alokasi", ["Paket Lengkap"] if role_p == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
        thn = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
        bln = st.selectbox("Bulan", bln_order)
        if st.form_submit_button("✅ Simpan Data"):
            if nom > 0:
                res = proses_bayar(nama_p, nom, thn, bln, tp, role_p, df_masuk)
                save_to_cloud("Pemasukan", pd.concat([df_masuk, res], ignore_index=True))
                st.success("Pembayaran Berhasil!")
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
                save_to_cloud("Pengeluaran", pd.concat([df_keluar, new_o], ignore_index=True))
                st.success("Tercatat!")
                st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("👥 Manajemen Anggota")
    
    # Membuat Tab untuk Tambah dan Hapus agar rapi
    tab_tambah, tab_hapus = st.tabs(["➕ Tambah Anggota", "🗑️ Hapus Anggota"])
    
    with tab_tambah:
        with st.form("add_w", clear_on_submit=True):
            nw = st.text_input("Nama Lengkap")
            rl = st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Simpan Anggota Baru"):
                if nw:
                    # Cek apakah nama sudah ada
                    if nw in df_warga['Nama'].values:
                        st.error("Nama tersebut sudah terdaftar!")
                    else:
                        new_row = pd.DataFrame([{'Nama': nw, 'Role': rl}])
                        df_updated = pd.concat([df_warga, new_row], ignore_index=True)
                        save_to_cloud("Warga", df_updated)
                        st.success(f"Berhasil menambah {nw}")
                        st.rerun()
                else:
                    st.warning("Nama tidak boleh kosong!")

    with tab_hapus:
        if not df_warga.empty:
            target_hapus = st.selectbox("Pilih Nama yang Akan Dihapus", sorted(df_warga['Nama'].tolist()))
            st.warning(f"Tindakan ini akan menghapus **{target_hapus}** dari daftar warga.")
            if st.button("🔥 Hapus Permanen"):
                df_updated = df_warga[df_warga['Nama'] != target_hapus]
                save_to_cloud("Warga", df_updated)
                st.success(f"{target_hapus} telah dihapus.")
                st.rerun()
        else:
            st.info("Daftar warga kosong.")

    st.divider()
    st.write("### 📜 Daftar Anggota Saat Ini")
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("Histori Transaksi")
    st.write("### Pemasukan")
    st.dataframe(df_masuk.sort_index(ascending=False), use_container_width=True)
