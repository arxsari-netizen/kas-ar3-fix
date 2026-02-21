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

# --- 2. CSS GLOBAL ---
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
        st.markdown(f"""
            <div style="text-align: center; border: 2px solid #D4AF37; padding: 20px; border-radius: 15px; background: white;">
                <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="60">
                <h3 style="margin:10px 0 0 0;">AR-ROYHAAN 3</h3>
                <p style="color:#B8860B; font-weight:700;">KAS MANAGEMENT</p>
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
                    else: st.error("Username/Password salah")

if not st.session_state['logged_in']:
    login()
    st.stop()

# --- 4. LOGIKA DATA ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=600)
def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    df = pd.DataFrame(worksheet.get_all_records())
    for col in ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']:
        if col in df.columns: 
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def clear_cache(): st.cache_data.clear()

def append_to_cloud(sheet_name, df_new):
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_rows(df_new.values.tolist())
    clear_cache()

def rewrite_cloud(sheet_name, df_full):
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df_full.columns.values.tolist()] + df_full.values.tolist())
    clear_cache()

def proses_bayar(nama, nominal, thn, bln, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx_bln = list_bulan.index(bln)
    sisa, data_baru = nominal, []
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
        if idx_bln > 11: idx_bln = 0; thn += 1
        if thn > 2030: break
    return pd.DataFrame(data_baru)

# LOAD DATA
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- SIDEBAR ---
st.sidebar.markdown(f"### 👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🔄 Refresh Data"): clear_cache(); st.rerun()
if st.sidebar.button("🚪 Logout"): st.session_state.clear(); st.rerun()

list_menu = ["📊 Laporan", "📥 Pemasukan", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Navigasi", list_menu)

# --- DASHBOARD METRIK ---
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()

st.markdown(f"## AR-ROYHAAN 3 DASHBOARD")
m1, m2, m3 = st.columns(3)
m1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
m3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")
st.divider()

# --- MENU LOGIC ---
if menu == "📊 Laporan":
    st.subheader("📋 Laporan Tahunan")
    thn_lap = st.selectbox("Pilih Tahun", list(range(2022, 2031)), index=4)
    tab1, tab2, tab3 = st.tabs(["📥 Pemasukan", "📤 Pengeluaran", "🏆 Ringkasan"])
    df_yr_in = df_masuk[df_masuk['Tahun'] == thn_lap]
    bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

    with tab1:
        if not df_yr_in.empty:
            st.write("### 💰 Dana KAS (Target Rp 15.000)")
            rk = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            cols_k = [b for b in bln_order if b in rk.columns]
            if cols_k:
                st.dataframe(rk[cols_k].style.highlight_between(left=15000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
            
            st.write("### 🎁 Dana HADIAH (Target Rp 35.000)")
            rh = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            cols_h = [b for b in bln_order if b in rh.columns]
            if cols_h:
                st.dataframe(rh[cols_h].style.highlight_between(left=35000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
        else: st.info("Data Kosong.")

    with tab2:
        df_keluar['Y'] = df_keluar['Tanggal'].apply(lambda d: int(str(d).split('/')[2].split(' ')[0]) if '/' in str(d) else 0)
        df_out_yr = df_keluar[df_keluar['Y'] == thn_lap]
        st.dataframe(df_out_yr[['Tanggal', 'Kategori', 'Jumlah', 'Keterangan']], use_container_width=True)

    with tab3:
        if not df_yr_in.empty:
            rekap = df_yr_in.groupby('Nama').agg({'Kas':'sum','Hadiah':'sum','Total':'sum'}).reset_index()
            st.table(rekap.style.format({"Kas": "{:,.0f}", "Hadiah": "{:,.0f}", "Total": "{:,.0f}"}))

elif menu == "📥 Pemasukan":
    st.subheader("📥 Input Pembayaran")
    
    if not df_warga.empty:
        # Pilihan nama di luar form biar role-nya update otomatis
        nama_sel = st.selectbox("Pilih Anggota", sorted(df_warga['Nama'].tolist()))
        role_sel = df_warga.loc[df_warga['Nama'] == nama_sel, 'Role'].values[0]
        
        with st.form("f_in", clear_on_submit=True):
            st.info(f"Target: **{nama_sel}** | Role: **{role_sel}**")
            
            col1, col2 = st.columns(2)
            with col1:
                nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
                tp = st.selectbox("Alokasi", ["Paket Lengkap"] if role_sel == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            
            with col2:
                th = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
                bl = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            
            # --- TOMBOL SUBMIT ---
            submit_bayar = st.form_submit_button("Simpan Pembayaran")
            
            if submit_bayar:
                if nom > 0:
                    # Jalankan fungsi simpan
                    res = proses_bayar(nama_sel, nom, th, bl, tp, role_sel, df_masuk)
                    append_to_cloud("Pemasukan", res)
                    
                    # --- NOTIF IJO DETAIL ---
                    st.success(f"✅ BERHASIL! Duit Rp {nom:,.0f} dari {nama_sel} sudah masuk ke Google Sheets.")
                    
                    # Kasih jeda 2 detik biar notif kebaca sebelum pindah halaman
                    import time
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Isi nominalnya dulu, Bro!")
    else:
        st.warning("Data warga kosong, isi dulu di menu Kelola Warga.")

elif menu == "📤 Pengeluaran":
    st.subheader("📤 Catat Pengeluaran")
    with st.form("f_out", clear_on_submit=True):
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah"])
        jml = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
        ket = st.text_input("Keterangan / Keperluan")
        
        submit_keluar = st.form_submit_button("Simpan Pengeluaran")
        
        if submit_keluar:
            if jml > 0 and ket:
                data_out = pd.DataFrame([{
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Kategori': kat,
                    'Jumlah': jml,
                    'Keterangan': ket
                }])
                append_to_cloud("Pengeluaran", data_out)
                st.success(f"✅ Pengeluaran Rp {jml:,.0f} Berhasil Dicatat!")
                import time
                time.sleep(2)
                st.rerun()
            else:
                st.error("Jumlah dan Keterangan harus diisi!")
elif menu == "👥 Kelola Warga":
    st.subheader("👥 Database Anggota")
    nw = st.text_input("Nama Baru")
    rl = st.selectbox("Role", ["Main Warga", "Warga Support"])
    if st.button("Tambah Warga"):
        rewrite_cloud("Warga", pd.concat([df_warga, pd.DataFrame([{'Nama': nw, 'Role': rl}])], ignore_index=True))
        st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("📜 History Transaksi")
    st.dataframe(df_masuk.sort_index(ascending=False), use_container_width=True)
