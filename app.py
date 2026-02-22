import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

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
                elif user == st.secrets["users"].get("inventaris_user") and pwd == st.secrets["users"].get("inventaris_password"):
                    st.session_state.update({"logged_in": True, "role": "admin_inventaris"}); st.rerun()
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
    cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df

df_masuk, df_keluar, df_warga, df_event = load_data("Pemasukan"), load_data("Pengeluaran"), load_data("Warga"), load_data("Event")
try: df_inv = load_data("Inventaris")
except: df_inv = pd.DataFrame(columns=['Nama Barang', 'Spesifikasi', 'Jumlah', 'Lokasi', 'Kondisi', 'Status'])

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=80)
    st.write(f"**USER: {st.session_state['role'].upper()}**")
    if st.session_state['role'] == "admin":
        list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📦 Inventaris", "📜 Log"]
    elif st.session_state['role'] == "admin_inventaris":
        list_menu = ["📊 Laporan", "📦 Inventaris"]
    else:
        list_menu = ["📊 Laporan", "📜 Log"]
    menu = st.radio("NAVIGASI", list_menu)
    if st.button("Logout"): st.session_state.clear(); st.rerun()

# --- 5. DASHBOARD ---
st.title(f"🏦 {menu}")
in_k, in_h, in_e = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum(), df_event['Jumlah'].sum()
out_k, out_h, out_e = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum(), df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum(), df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 SALDO KAS", f"Rp {int(in_k - out_k):,}")
m2.metric("🎁 SALDO HADIAH", f"Rp {int(in_h - out_h):,}")
m3.metric("🎭 SALDO EVENT", f"Rp {int(in_e - out_e):,}")
m4.metric("🏧 TOTAL TUNAI", f"Rp {int((in_k+in_h+in_e)-(out_k+out_h+out_e)):,}")
st.divider()

bln_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

# --- 6. LOGIKA MENU ---

if menu == "📊 Laporan":
    t1, t2, t3 = st.tabs(["💰 Rekap Bulanan", "🎭 Detail Event", "📤 Riwayat Pengeluaran"])
    with t1:
        thn = st.selectbox("Tahun", range(2022, 2031), index=4)
        df_y = df_masuk[df_masuk['Tahun'] == thn]
        st.write("#### 🟢 Kas (15rb)")
        if not df_y.empty: st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0).astype(int).reindex(columns=[b for b in bln_list if b in df_y['Bulan'].unique()]), use_container_width=True)
        st.write("#### 🟡 Hadiah (35rb)")
        if not df_y.empty: st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0).astype(int).reindex(columns=[b for b in bln_list if b in df_y['Bulan'].unique()]), use_container_width=True)
    with t2:
        if not df_event.empty:
            ev_sel = st.selectbox("Pilih Event", df_event['Nama Event'].unique())
            e_in = df_event[df_event['Nama Event'] == ev_sel]['Jumlah'].sum()
            e_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(f"[{ev_sel}]"))]['Jumlah'].sum()
            c1, c2, c3 = st.columns(3); c1.metric("Masuk", f"Rp {int(e_in):,}"); c2.metric("Keluar", f"Rp {int(e_out):,}"); c3.metric("Sisa", f"Rp {int(e_in - e_out):,}")
            col_in, col_out = st.columns(2)
            with col_in: st.write("**📥 Iuran:**"); st.dataframe(df_event[df_event['Nama Event'] == ev_sel][['Tanggal', 'Nama', 'Jumlah']], hide_index=True)
            with col_out: st.write("**📤 Belanja:**"); st.dataframe(df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(f"[{ev_sel}]"))][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True)
    with t3:
        ck, ch = st.columns(2)
        with ck: st.write("#### 📤 Pengeluaran KAS"); st.dataframe(df_keluar[df_keluar['Kategori'] == 'Kas'][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True, use_container_width=True)
        with ch: st.write("#### 📤 Pengeluaran HADIAH"); st.dataframe(df_keluar[df_keluar['Kategori'] == 'Hadiah'][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True, use_container_width=True)

elif menu == "📤 Pengeluaran":
    kat_pilih = st.radio("Sumber Dana:", ["Kas", "Hadiah", "Event"], horizontal=True)
    with st.form("f_out", clear_on_submit=True):
        ev_ref = "N/A"
        if kat_pilih == "Event":
            ev_list = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
            ev_ref = st.selectbox("Wajib Pilih Event:", ["-- Pilih Event --"] + ev_list)
        nom = st.number_input("Nominal", min_value=0, step=1000, key="nom_out")
        ket = st.text_input("Keterangan")
        if st.form_submit_button("Simpan"):
            if kat_pilih == "Event" and ev_ref == "-- Pilih Event --": st.error("Pilih Event!")
            elif nom <= 0: st.error("Isi Nominal!")
            else:
                sh.worksheet("Pengeluaran").append_row([datetime.now().strftime("%d/%m/%Y"), kat_pilih, int(nom), f"[{ev_ref}] {ket}" if kat_pilih == "Event" else ket])
                st.success("Tercatat!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "📥 Kas Bulanan":
    w_pilih = st.selectbox("Nama Warga", sorted(df_warga['Nama'].tolist()), key="sw")
    role_w = df_warga[df_warga['Nama'] == w_pilih]['Role'].values[0] if w_pilih in df_warga['Nama'].values else "Main Warga"
    with st.form("f_kas", clear_on_submit=True):
        n = st.number_input("Nominal", step=5000, key="n_kas")
        t, b = st.selectbox("Tahun", range(2022, 2031), index=4), st.selectbox("Bulan", bln_list)
        opsi = st.radio("Bayar:", ["Semua", "Hanya Kas", "Hanya Hadiah"], horizontal=True) if role_w == "Warga Support" else "Semua"
        if st.form_submit_button("Simpan"):
            pk, ph = (n, 0) if opsi=="Hanya Kas" else (0, n) if opsi=="Hanya Hadiah" else (min(n, 15000), max(0, n-15000))
            sh.worksheet("Pemasukan").append_row([datetime.now().strftime("%d/%m/%Y"), w_pilih, t, b, int(n), int(pk), int(ph), "LUNAS"])
            st.success("OK!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "📦 Inventaris":
    st.subheader("📦 Manajemen Aset Majelis")
    tab_view, tab_add, tab_edit = st.tabs(["📋 Daftar", "➕ Tambah", "✏️ Update"])
    with tab_view:
        if not df_inv.empty:
            pilih_lok = st.selectbox("Filter Lokasi", ["Semua"] + df_inv['Lokasi'].unique().tolist())
            st.dataframe(df_inv if pilih_lok == "Semua" else df_inv[df_inv['Lokasi'] == pilih_lok], hide_index=True, use_container_width=True)
    with tab_add:
        with st.form("f_inv_add", clear_on_submit=True):
            nb, sp = st.text_input("Nama Barang"), st.text_input("Spesifikasi")
            jml, lok = st.number_input("Jumlah", min_value=1), st.text_input("Lokasi")
            kon, sts = st.selectbox("Kondisi", ["Baik", "Rusak"]), st.selectbox("Status", ["Tersedia", "Dipinjam"])
            if st.form_submit_button("Simpan"):
                sh.worksheet("Inventaris").append_row([nb, sp, int(jml), lok, kon, sts])
                st.success("Tersimpan!"); st.cache_data.clear(); time.sleep(1); st.rerun()
    with tab_edit:
        if not df_inv.empty:
            with st.form("f_inv_edit"):
                b_edit = st.selectbox("Pilih Barang", df_inv['Nama Barang'].tolist())
                n_k, n_s = st.selectbox("Kondisi Baru", ["Baik", "Rusak"]), st.selectbox("Status Baru", ["Tersedia", "Dipinjam"])
                if st.form_submit_button("Update"):
                    row = sh.worksheet("Inventaris").find(b_edit).row
                    sh.worksheet("Inventaris").update_cell(row, 5, n_k); sh.worksheet("Inventaris").update_cell(row, 6, n_s)
                    st.success("Updated!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "🎭 Event & Iuran":
    with st.form("f_ev", clear_on_submit=True):
        ev_ada = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
        ev_p = st.selectbox("Event", ["-- Baru --"] + ev_ada)
        ev_n = st.text_input("Nama Event Baru") if ev_p == "-- Baru --" else ev_p
        w_e, j_e = st.selectbox("Warga", sorted(df_warga['Nama'].tolist())), st.number_input("Jumlah", step=5000)
        if st.form_submit_button("Simpan"):
            sh.worksheet("Event").append_row([datetime.now().strftime("%d/%m/%Y"), w_e, ev_n, int(j_e)])
            st.success("OK!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "👥 Kelola Warga":
    st.dataframe(df_warga[['Nama', 'Role']], hide_index=True, use_container_width=True)
    ct, ce, ch = st.tabs(["➕ Tambah", "✏️ Edit", "🗑️ Hapus"])
    with ct:
        with st.form("t_w"):
            nw, nr = st.text_input("Nama"), st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Tambah"): sh.worksheet("Warga").append_row([nw, nr]); st.rerun()
    with ce:
        with st.form("e_w"):
            w_o = st.selectbox("Warga", df_warga['Nama'].tolist())
            w_n, r_n = st.text_input("Nama Baru"), st.selectbox("Role Baru", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Update"):
                row = sh.worksheet("Warga").find(w_o).row
                sh.worksheet("Warga").update_cell(row, 1, w_n); sh.worksheet("Warga").update_cell(row, 2, r_n); st.rerun()
    with ch:
        with st.form("h_w"):
            w_d = st.selectbox("Hapus", df_warga['Nama'].tolist())
            if st.form_submit_button("Hapus"): sh.worksheet("Warga").delete_rows(sh.worksheet("Warga").find(w_d).row); st.rerun()

elif menu == "📜 Log":
    st.dataframe(df_masuk.tail(20), hide_index=True, use_container_width=True)
