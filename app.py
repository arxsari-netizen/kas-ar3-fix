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

# --- 2. CSS GLOBAL ---
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

@st.cache_data(ttl=300)
def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    df = pd.DataFrame(worksheet.get_all_records())
    numeric_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in numeric_cols:
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
df_event = load_data("Event")

# --- 5. SIDEBAR & NAVIGASI ---
st.sidebar.markdown(f"### 👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🔄 Refresh Data"): clear_cache(); st.rerun()
if st.sidebar.button("🚪 Logout"): st.session_state.clear(); st.rerun()

list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Navigasi Utama", list_menu)

# --- 6. DASHBOARD METRIK ---
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()

in_ev_total = df_event['Jumlah'].sum() if not df_event.empty else 0
out_ev_total = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum() if not df_keluar.empty else 0
saldo_event_bersih = in_ev_total - out_ev_total

st.markdown(f"## 🏦 KAS & EVENT AR-ROYHAAN 3")
m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
m3.metric("🎭 SALDO EVENT", f"Rp {saldo_event_bersih:,.0f}")
m4.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h+in_ev_total)-(out_k+out_h+out_ev_total):,.0f}")
st.divider()

# --- 7. LOGIKA MENU ---

if menu == "📊 Laporan":
    st.subheader("📋 Laporan Keuangan")
    tab1, tab2, tab3 = st.tabs(["💰 Kas & Hadiah Bulanan", "🎭 Saldo Per Event", "📤 Riwayat Pengeluaran"])
    
    with tab1:
        st.write("### 📅 Rekap Kas & Hadiah (Tahun ini)")
        thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
        df_yr = df_masuk[df_masuk['Tahun'] == thn_lap]
        if not df_yr.empty:
            rk = df_yr.pivot_table(index='Nama', columns='Bulan', values='Total', aggfunc='sum').fillna(0)
            bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            cols = [b for b in bln_order if b in rk.columns]
            st.dataframe(rk[cols].style.highlight_between(left=50000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
        else:
            st.info("Data tahun ini kosong.")

    with tab2:
        st.write("### 🎭 Detail Saldo Tiap Event")
        if not df_event.empty:
            ev_list = df_event['Nama Event'].unique().tolist()
            ev_sel = st.selectbox("Pilih Event", ev_list)
            
            ev_in = df_event[df_event['Nama Event'] == ev_sel]['Jumlah'].sum()
            ev_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(ev_sel, na=False))]['Jumlah'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Iuran Masuk", f"Rp {ev_in:,.0f}")
            c2.metric("Total Belanja Keluar", f"Rp {ev_out:,.0f}")
            c3.metric("Sisa Saldo Event", f"Rp {ev_in - ev_out:,.0f}")
            
            st.write(f"**Daftar Penyumbang {ev_sel}:**")
            st.dataframe(df_event[df_event['Nama Event'] == ev_sel][['Tanggal', 'Nama', 'Jumlah']], use_container_width=True)
        else:
            st.info("Belum ada data event.")

    with tab3:
        st.write("### 📤 Laporan Semua Pengeluaran")
        kat_f = st.multiselect("Filter Sumber Dana:", ["Kas", "Hadiah", "Event"], default=["Kas", "Hadiah", "Event"])
        df_f = df_keluar[df_keluar['Kategori'].isin(kat_f)]
        st.dataframe(df_f[['Tanggal', 'Kategori', 'Jumlah', 'Keterangan']].sort_values('Tanggal', ascending=False), use_container_width=True)

elif menu == "📥 Kas Bulanan":
    st.subheader("📥 Input Kas Bulanan")
    if not df_warga.empty:
        nama_sel = st.selectbox("Pilih Warga", sorted(df_warga['Nama'].tolist()))
        role_sel = df_warga.loc[df_warga['Nama'] == nama_sel, 'Role'].values[0]
        with st.form("f_kas"):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
                tp = st.selectbox("Alokasi", ["Paket Lengkap"] if role_sel == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            with col2:
                th = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
                bl = st.selectbox("Mulai Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            if st.form_submit_button("Simpan Kas"):
                if nom > 0:
                    res = proses_bayar(nama_sel, nom, th, bl, tp, role_sel, df_masuk)
                    append_to_cloud("Pemasukan", res)
                    st.success("✅ Data Kas Berhasil Disimpan!")
                    time.sleep(1); st.rerun()

elif menu == "🎭 Event & Iuran":
    st.subheader("🎭 Iuran Khusus Event")
    if not df_warga.empty:
        list_ev_ada = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            ev_p = st.selectbox("Nama Event", ["-- Pilih --"] + list_ev_ada + ["➕ Tambah Baru"])
            ev_f = st.text_input("Ketik Nama Event Baru") if ev_p == "➕ Tambah Baru" else ev_p
        with col_e2:
            warga_e = st.selectbox("Nama Warga", sorted(df_warga['Nama'].tolist()), key="w_ev")
        with st.form("f_ev"):
