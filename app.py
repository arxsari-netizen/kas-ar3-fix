import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. CONFIG & THEME ---
st.set_page_config(
    page_title="AR-ROYHAAN 3 KAS & EVENT",
    page_icon="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png",
    layout="wide"
)

st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px;
    }
    .stTabs [aria-selected="true"] { background-color: #D4AF37 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE & LOGIN ---
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
            submit = st.form_submit_button("Masuk Ke Aplikasi")
            if submit:
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

# --- 3. GOOGLE SHEETS ENGINE ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=60)
def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    df = pd.DataFrame(worksheet.get_all_records())
    numeric_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in numeric_cols:
        if col in df.columns: 
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def append_to_cloud(sheet_name, df_new):
    sh.worksheet(sheet_name).append_rows(df_new.values.tolist())
    st.cache_data.clear()

# --- 4. LOAD SEMUA DATA ---
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")
df_event = load_data("Event")

# --- 5. SIDEBAR NAVIGASI (LOCK) ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=100)
    st.markdown(f"**👤 ROLE: {st.session_state['role'].upper()}**")
    st.divider()
    
    if st.session_state['role'] == "admin":
        list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"]
    else:
        list_menu = ["📊 Laporan", "📜 Log"]
    
    menu = st.radio("NAVIGASI UTAMA", list_menu)
    st.divider()
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
    if st.button("🚪 Logout"): st.session_state.clear(); st.rerun()

# --- 6. DASHBOARD 4 METRIK ---
st.markdown(f"## 🏦 DASHBOARD {menu.upper()}")
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
in_ev = df_event['Jumlah'].sum() if not df_event.empty else 0
out_ev = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 SALDO KAS (15rb)", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH (35rb)", f"Rp {in_h - out_h:,.0f}")
m3.metric("🎭 SALDO EVENT", f"Rp {in_ev - out_ev:,.0f}")
m4.metric("🏧 TOTAL TUNAI", f"Rp {(in_k+in_h+in_ev)-(out_k+out_h+out_ev):,.0f}")
st.divider()

# --- 7. LOGIKA KONTEN ---
list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

if menu == "📊 Laporan":
    tab1, tab2 = st.tabs(["💰 Kas & Hadiah Bulanan", "🎭 Detail Event"])
    with tab1:
        thn_lap = st.selectbox("Pilih Tahun Laporan", list(range(2022, 2031)), index=4)
        df_yr = df_masuk[df_masuk['Tahun'] == thn_lap]
        
        st.markdown("### 🟢 LAPORAN KAS (15rb)")
        if not df_yr.empty:
            rk_k = df_yr.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            st.dataframe(rk_k.reindex(columns=[b for b in list_bulan if b in rk_k.columns]), use_container_width=True)
        else: st.info("Tidak ada data Kas di tahun ini.")
        
        st.divider()
        st.markdown("### 🟡 LAPORAN HADIAH (35rb)")
        if not df_yr.empty:
            rk_h = df_yr.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            st.dataframe(rk_h.reindex(columns=[b for b in list_bulan if b in rk_h.columns]), use_container_width=True)
        else: st.info("Tidak ada data Hadiah di tahun ini.")

    with tab2:
        st.write("### 🎭 Detail Saldo Tiap Event")
        if not df_event.empty:
            ev_list = df_event['Nama Event'].unique().tolist()
            ev_sel = st.selectbox("Pilih Event Untuk Dilihat", ev_list)
            
            ev_in = df_event[df_event['Nama Event'] == ev_sel]['Jumlah'].sum()
            ev_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(ev_sel, na=False))]['Jumlah'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Iuran Masuk", f"Rp {ev_in:,.0f}")
            c2.metric("Total Belanja Keluar", f"Rp {ev_out:,.0f}")
            c3.metric("Sisa Saldo Event", f"Rp {ev_in - ev_out:,.0f}")
            
            st.write(f"**Riwayat Iuran {ev_sel}:**")
            st.dataframe(df_event[df_event['Nama Event'] == ev_sel][['Tanggal', 'Nama', 'Jumlah']], use_container_width=True)
        else:
            st.info("Belum ada data event.")

elif menu == "📥 Kas Bulanan":
    st.subheader("📥 Input Kas & Hadiah")
    if not df_warga.empty:
        with st.form("form_pemasukan"):
            c1, c2 = st.columns(2)
            with c1:
                nama_s = st.selectbox("Pilih Warga", sorted(df_warga['Nama'].tolist()))
                nom = st.number_input("Nominal Bayar (Total)", min_value=0, step=5000)
            with c2:
                th_s = st.selectbox("Tahun", list(range(2022, 2031)), index=4)
                bl_s = st.selectbox("Bulan", list_bulan)
            submit_k = st.form_submit_button("💰 SIMPAN PEMBAYARAN")
            if submit_k:
                if nom > 0:
                    p_kas = 15000 if nom >= 15000 else nom
                    p_hadiah = nom - p_kas
                    new_row = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Nama': nama_s, 'Tahun': th_s, 'Bulan': bl_s, 'Total': nom, 'Kas': p_kas, 'Hadiah': p_hadiah, 'Status': 'LUNAS' if nom >= 50000 else 'CICIL'}])
                    append_to_cloud("Pemasukan", new_row)
                    st.success(f"Berhasil disimpan!")
                    time.sleep(1); st.rerun()

elif menu == "🎭 Event & Iuran":
    st.subheader("🎭 Input Iuran Event")
    list_ev_ada = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
    with st.form("form_event"):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            ev_p = st.selectbox("Pilih Event", ["-- Event Baru --"] + list_ev_ada)
            ev_input = st.text_input("Atau Ketik Nama Event Baru")
        with col_e2:
            warga_e = st.selectbox("Nama Warga", sorted(df_warga['Nama'].tolist()))
            nom_e = st.number_input("Nominal Iuran", min_value=0, step=5000)
        ev_final = ev_input if ev_p == "-- Event Baru --" else ev_p
        submit_e = st.form_submit_button("🚀 SIMPAN IURAN EVENT")
        if submit_e:
            if nom_e > 0 and ev_final:
                new_ev = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Nama': warga_e, 'Nama Event': ev_final, 'Jumlah': nom_e}])
                append_to_cloud("Event", new_ev)
                st.success(f"Iuran {ev_final} berhasil disimpan!")
                time.sleep(1); st.rerun()

elif menu == "📤 Pengeluaran":
    st.subheader("📤 Catat Pengeluaran")
    with st.form("form_pengeluaran"):
        kat_o = st.selectbox("Sumber Dana", ["Kas", "Hadiah", "Event"])
        jml_o = st.number_input("Nominal Keluar", min_value=0, step=1000)
        ket_o = st.text_input("Keterangan Pengeluaran")
        submit_o = st.form_submit_button("🛑 SIMPAN PENGELUARAN")
        if submit_o:
            if jml_o > 0 and ket_o:
                new_out = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat_o, 'Jumlah': jml_o, 'Keterangan': ket_o}])
                append_to_cloud("Pengeluaran", new_out)
                st.success("Pengeluaran berhasil dicatat!")
                time.sleep(1); st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("👥 Database Warga")
    with st.form("form_warga"):
        nw = st.text_input("Nama Lengkap Warga Baru")
        rl = st.selectbox("Role", ["Main Warga", "Warga Support"])
        submit_w = st.form_submit_button("➕ TAMBAH WARGA")
        if submit_w and nw:
            append_to_cloud("Warga", pd.DataFrame([{'Nama': nw, 'Role': rl}]))
            st.success("Warga berhasil ditambah!")
            st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("📜 Riwayat Transaksi")
    tab_l1, tab_l2 = st.tabs(["Pemasukan Kas", "Iuran Event"])
    with tab_l1: st.dataframe(df_masuk.sort_index(ascending=False).head(30), use_container_width=True)
    with tab_l2: st.dataframe(df_event.sort_index(ascending=False).head(30), use_container_width=True)
