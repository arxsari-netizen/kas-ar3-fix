import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="AR-ROYHAAN 3", layout="wide")
st.markdown("""<style>header {visibility: hidden;} .stApp { background-color: #f8f9fa; } [data-testid="stMetric"] { background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px; }</style>""", unsafe_allow_html=True)

# --- 2. LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.update({'logged_in': False, 'role': None})
if not st.session_state['logged_in']:
    _, col_mid, _ = st.columns([0.1, 1, 0.1])
    with col_mid:
        st.markdown('<div style="text-align: center; border: 2px solid #D4AF37; padding: 20px; border-radius: 15px; background: white;"><h3>AR-ROYHAAN 3</h3><p>LOGIN SYSTEM</p></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            user, pwd = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                if user == st.secrets["users"]["admin_user"] and pwd == st.secrets["users"]["admin_password"]:
                    st.session_state.update({"logged_in": True, "role": "admin"}); st.rerun()
                elif user == st.secrets["users"]["warga_user"] and pwd == st.secrets["users"]["warga_password"]:
                    st.session_state.update({"logged_in": True, "role": "user"}); st.rerun()
                else: st.error("Akses Ditolak!")
    st.stop()

# --- 3. DATA ENGINE ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=30)
def load_data(sheet_name):
    ws = sh.worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    for col in ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df

df_masuk, df_keluar, df_warga, df_event = load_data("Pemasukan"), load_data("Pengeluaran"), load_data("Warga"), load_data("Event")

# --- 4. DASHBOARD ---
st.title(f"🏦 {menu if 'menu' in locals() else 'Dashboard'}")
in_k, in_h, in_e = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum(), df_event['Jumlah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
out_e = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 SALDO KAS", f"Rp {int(in_k - out_k):,}")
m2.metric("🎁 SALDO HADIAH", f"Rp {int(in_h - out_h):,}")
m3.metric("🎭 SALDO EVENT", f"Rp {int(in_e - out_e):,}")
m4.metric("🏧 TOTAL TUNAI", f"Rp {int((in_k+in_h+in_e)-(out_k+out_h+out_e)):,}")
st.divider()

# --- 5. SIDEBAR & MENU ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=80)
    st.write(f"**USER: {st.session_state['role'].upper()}**")
    list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role']=="admin" else ["📊 Laporan", "📜 Log"]
    menu = st.radio("NAVIGASI", list_menu)
    if st.button("Logout"): st.session_state.clear(); st.rerun()

bln_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

if menu == "📊 Laporan":
    t1, t2, t3 = st.tabs(["💰 Rekap Bulanan", "🎭 Detail Event", "📤 Riwayat Pengeluaran"])
    
    with t1:
        thn = st.selectbox("Pilih Tahun Laporan", range(2022, 2031), index=4)
        df_y = df_masuk[df_masuk['Tahun'] == thn]
        st.write("#### 🟢 Kas (15rb)")
        if not df_y.empty: st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0).astype(int).reindex(columns=[b for b in bln_list if b in df_y['Bulan'].unique()]), use_container_width=True)
        st.write("#### 🟡 Hadiah (35rb)")
        if not df_y.empty: st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0).astype(int).reindex(columns=[b for b in bln_list if b in df_y['Bulan'].unique()]), use_container_width=True)
    
    with t2:
        if not df_event.empty:
            ev_sel = st.selectbox("Pilih Nama Event", df_event['Nama Event'].unique())
            e_in = df_event[df_event['Nama Event'] == ev_sel]['Jumlah'].sum()
            e_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(f"[{ev_sel}]"))]['Jumlah'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Iuran Masuk", f"Rp {int(e_in):,}")
            c2.metric("Pengeluaran", f"Rp {int(e_out):,}")
            c3.metric("SISA SALDO", f"Rp {int(e_in - e_out):,}")
            
            col_in, col_out = st.columns(2)
            with col_in:
                st.write("**📥 Rincian Iuran Warga:**")
                st.dataframe(df_event[df_event['Nama Event'] == ev_sel][['Tanggal', 'Nama', 'Jumlah']], hide_index=True)
            with col_out:
                st.write("**📤 Rincian Belanja Event:**")
                st.dataframe(df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(f"[{ev_sel}]"))][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True)

    with t3: # PERBAIKAN: LAPORAN PENGELUARAN DIPISAH
        col_k, col_h = st.columns(2)
        with col_k:
            st.write("#### 📤 Pengeluaran DANA KAS")
            df_k = df_keluar[df_keluar['Kategori'] == 'Kas']
            st.dataframe(df_k[['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True, use_container_width=True)
            st.info(f"Total Keluar Kas: Rp {int(df_k['Jumlah'].sum()):,}")
        with col_h:
            st.write("#### 📤 Pengeluaran DANA HADIAH")
            df_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']
            st.dataframe(df_h[['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True, use_container_width=True)
            st.info(f"Total Keluar Hadiah: Rp {int(df_h['Jumlah'].sum()):,}")

elif menu == "📤 Pengeluaran":
    with st.form("f_out"):
        kat = st.selectbox("Kategori Dana", ["Kas", "Hadiah", "Event"])
        ev_list = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
        ev_ref = st.selectbox("Pilih Event (WAJIB jika Kategori = Event)", ["-- Pilih Event --"] + ev_list)
        nom, ket = st.number_input("Nominal", min_value=0, step=1000), st.text_input("Keterangan Barang/Jasa")
        
        if st.form_submit_button("Catat Pengeluaran"):
            # PERBAIKAN: Validasi agar tidak N/A saat pilih Event
            if kat == "Event" and ev_ref == "-- Pilih Event --":
                st.error("❌ Gagal! Lu harus pilih nama Event-nya dulu kalau mau pake Dana Event.")
            elif nom <= 0:
                st.error("❌ Nominal gak boleh nol!")
            else:
                final_ket = f"[{ev_ref}] {ket}" if kat == "Event" else ket
                sh.worksheet("Pengeluaran").append_row([datetime.now().strftime("%d/%m/%Y"), kat, int(nom), final_ket])
                st.success("Tercatat!"); st.cache_data.clear(); st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("Data Warga & Role")
    st.dataframe(df_warga[['Nama', 'Role']], hide_index=True, use_container_width=True)
    ct, ce, ch = st.tabs(["➕ Tambah", "✏️ Edit", "🗑️ Hapus"])
    with ct:
        with st.form("t_w"):
            nw = st.text_input("Nama Baru")
            nr = st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Tambah"):
                sh.worksheet("Warga").append_row([nw, nr]); st.rerun()
    with ce:
        with st.form("e_w"):
            w_o = st.selectbox("Warga", df_warga['Nama'].tolist())
            w_n, r_n = st.text_input("Nama Baru"), st.selectbox("Role Baru", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Update"):
                cell = sh.worksheet("Warga").find(w_o)
                sh.worksheet("Warga").update_cell(cell.row, 1, w_n)
                sh.worksheet("Warga").update_cell(cell.row, 2, r_n); st.rerun()
    with ch:
        with st.form("h_w"):
            w_d = st.selectbox("Hapus", df_warga['Nama'].tolist())
            if st.form_submit_button("Hapus Permanen"):
                cell = sh.worksheet("Warga").find(w_d)
                sh.worksheet("Warga").delete_rows(cell.row); st.rerun()

elif menu == "📜 Log":
    st.write("Riwayat Pemasukan Terakhir")
    st.dataframe(df_masuk.tail(20), hide_index=True, use_container_width=True)
