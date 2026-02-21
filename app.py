import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time  # Pindahkan ke sini biar rapi

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
    st.markdown("""<style>.main-login-container { max-width: 420px; margin: auto; padding-top: 50px; }</style>""", unsafe_allow_html=True)
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
    numeric_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in numeric_cols:
        if col in df.columns: 
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def clear_cache():
    st.cache_data.clear()

def append_to_cloud(sheet_name, df_new):
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_rows(df_new.values.tolist())
    clear_cache()

def rewrite_cloud(sheet_name, df_full):
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df_full.columns.values.tolist()] + df_full.values.tolist())
    clear_cache()

# --- 5. LOGIKA BAYAR ---
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
            idx_bln = 0; thn += 1
        if thn > 2030: break
    return pd.DataFrame(data_baru)

# LOAD DATA
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- SIDEBAR ---
st.sidebar.markdown(f"### 👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🔄 Refresh Data"):
    clear_cache()
    st.rerun()
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

list_menu = ["📊 Laporan", "📥 Pemasukan", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Navigasi", list_menu)

# --- METRIK ---
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
        def get_yr(d):
            try: return int(str(d).split('/')[2].split(' ')[0])
            except: return 0
        df_keluar['Y'] = df_keluar['Tanggal'].apply(get_yr)
        df_out_yr = df_keluar[df_keluar['Y'] == thn_lap]
        if not df_out_yr.empty:
            st.metric("Total Pengeluaran", f"Rp {df_out_yr['Jumlah'].sum():,.0f}")
            st.dataframe(df_out_yr[['Tanggal', 'Kategori', 'Jumlah', 'Keterangan']], use_container_width=True)

    with tab3:
        if not df_yr_in.empty:
            rekap = df_yr_in.groupby('Nama').agg({'Kas':'sum','Hadiah':'sum','Total':'sum'}).reset_index()
            rekap['Status'] = rekap['Total'].apply(lambda x: "✅ LUNAS" if x >= 600000 else f"⚠️ Kurang Rp {600000-x:,.0f}")
            st.table(rekap.style.format({"Kas": "{:,.0f}", "Hadiah": "{:,.0f}", "Total": "{:,.0f}"}))

elif menu == "📥 Pemasukan":
    st.subheader("📥 Input Pembayaran")
    if not df_warga.empty:
        nama_sel = st.selectbox("Pilih Anggota", sorted(df_warga['Nama'].tolist()))
        role_sel = df_warga.loc[df_warga['Nama'] == nama_sel, 'Role'].values[0]
        with st.form("f_in", clear_on_submit=True):
            st.info(f"Target: **{nama_sel}** | Role: **{role_sel}**")
            col1, col2 = st.columns(2)
            with col1:
                nom = st.number_input("Nominal (Rp)", min_value=0, step=5000, format="%d")
                st.markdown(f"**Format: Rp {nom:,.0f}**")
                tp = st.selectbox("Alokasi", ["Paket Lengkap"] if role_sel == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            with col2:
                th = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
                bl = st.selectbox("Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            
            if st.form_submit_button("Simpan Pembayaran"):
                if nom > 0:
                    res = proses_bayar(nama_sel, nom, th, bl, tp, role_sel, df_masuk)
                    append_to_cloud("Pemasukan", res)
                    bln_awal, bln_akhir = res['Bulan'].iloc[0], res['Bulan'].iloc[-1]
                    rentang = f"Bulan {bln_awal}" if len(res) == 1 else f"{bln_awal} s/d {bln_akhir}"
                    st.success(f"✅ Tersimpan!\n* Nama: {nama_sel}\n* Total: Rp {nom:,.0f}\n* Alokasi: {rentang}")
                    time.sleep(2)
                    st.rerun()
                else: st.error("Nominal tidak boleh 0!")
    else: st.warning("Tambah warga dulu!")

elif menu == "📤 Pengeluaran":
    with st.form("f_out", clear_on_submit=True):
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah"])
        jml = st.number_input("Jumlah (Rp)", min_value=0, step=1000, format="%d")
        st.info(f"Dicatat: **Rp {jml:,.0f}**")
        ket = st.text_input("Keterangan")
        if st.form_submit_button("Simpan Pengeluaran"):
            if jml > 0 and ket:
                append_to_cloud("Pengeluaran", pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat, 'Jumlah': jml, 'Keterangan': ket}]))
                st.success("Tercatat!")
                time.sleep(1)
                st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("👥 Database Anggota")
    t1, t2, t3 = st.tabs(["➕ Tambah", "✏️ Edit", "🗑️ Hapus"])
    with t1:
        with st.form("f_add", clear_on_submit=True):
            nw, rl = st.text_input("Nama"), st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Simpan"):
                if nw.strip():
                    rewrite_cloud("Warga", pd.concat([df_warga, pd.DataFrame([{'Nama': nw, 'Role': rl}])], ignore_index=True))
                    st.rerun()
    with t2:
        if not df_warga.empty:
            n_lama = st.selectbox("Pilih Nama", sorted(df_warga['Nama'].tolist()))
            data_w = df_warga[df_warga['Nama'] == n_lama].iloc[0]
            with st.form("f_edit"):
                n_baru = st.text_input("Nama Baru", value=data_w['Nama'])
                r_baru = st.selectbox("Role Baru", ["Main Warga", "Warga Support"], index=0 if data_w['Role'] == "Main Warga" else 1)
                if st.form_submit_button("Update"):
                    df_warga.loc[df_warga['Nama'] == n_lama, ['Nama', 'Role']] = [n_baru, r_baru]
                    rewrite_cloud("Warga", df_warga)
                    if not df_masuk.empty:
                        df_masuk.loc[df_masuk['Nama'] == n_lama, 'Nama'] = n_baru
                        rewrite_cloud("Pemasukan", df_masuk)
                    st.rerun()
    with t3:
        if not df_warga.empty:
            n_del = st.selectbox("Hapus Nama", sorted(df_warga['Nama'].tolist()))
            if st.button("Hapus Permanen") and st.checkbox(f"Yakin hapus {n_del}"):
                rewrite_cloud("Warga", df_warga[df_warga['Nama'] != n_del])
                st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("📜 History Transaksi")
    st.dataframe(df_masuk.sort_index(ascending=False), use_container_width=True)
