import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. CONFIG & THEME ---
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
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

df_masuk, df_keluar, df_warga, df_event = load_data("Pemasukan"), load_data("Pengeluaran"), load_data("Warga"), load_data("Event")

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=80)
    st.write(f"**USER: {st.session_state['role'].upper()}**")
    list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role']=="admin" else ["📊 Laporan", "📜 Log"]
    menu = st.radio("NAVIGASI", list_menu)
    if st.button("Logout"): st.session_state.clear(); st.rerun()

# --- 5. DASHBOARD ---
st.title(f"🏦 {menu}")
in_k, in_h, in_e = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum(), df_event['Jumlah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
out_e = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 KAS", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 HADIAH", f"Rp {in_h - out_h:,.0f}")
m3.metric("🎭 EVENT", f"Rp {in_e - out_e:,.0f}")
m4.metric("🏧 TOTAL", f"Rp {(in_k+in_h+in_e)-(out_k+out_h+out_e):,.0f}")
st.divider()

# --- 6. KONTEN ---
bln_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

if menu == "📊 Laporan":
    t1, t2 = st.tabs(["💰 Kas & Hadiah", "🎭 Detail Event"])
    with t1:
        thn = st.selectbox("Tahun", range(2022, 2031), index=4)
        df_y = df_masuk[df_masuk['Tahun'] == thn]
        st.write("#### 🟢 Laporan Kas (15rb)")
        if not df_y.empty: st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0).reindex(columns=[b for b in bln_list if b in df_y['Bulan'].unique()]), use_container_width=True)
        st.write("#### 🟡 Laporan Hadiah (35rb)")
        if not df_y.empty: st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0).reindex(columns=[b for b in bln_list if b in df_y['Bulan'].unique()]), use_container_width=True)
    with t2:
        if not df_event.empty:
            ev_sel = st.selectbox("Pilih Event", df_event['Nama Event'].unique())
            e_in = df_event[df_event['Nama Event'] == ev_sel]['Jumlah'].sum()
            e_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(ev_sel, case=False, na=False))]['Jumlah'].sum()
            
            c1, c2 = st.columns(2)
            c1.metric(f"Iuran Masuk {ev_sel}", f"Rp {e_in:,.0f}")
            c2.metric(f"Pengeluaran {ev_sel}", f"Rp {e_out:,.0f}")
            
            col_in, col_out = st.columns(2)
            with col_in:
                st.write("**📥 Rincian Iuran Warga:**")
                st.dataframe(df_event[df_event['Nama Event'] == ev_sel][['Tanggal', 'Nama', 'Jumlah']], hide_index=True)
            with col_out:
                st.write("**📤 Rincian Belanja Event:**")
                st.dataframe(df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(ev_sel, case=False, na=False))][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True)
        else: st.info("Belum ada data event.")

elif menu == "📥 Kas Bulanan":
    with st.form("f_kas"):
        w, n = st.selectbox("Warga", sorted(df_warga['Nama'].tolist())), st.number_input("Nominal", step=5000)
        t, b = st.selectbox("Tahun", range(2022, 2031), index=4), st.selectbox("Bulan", bln_list)
        if st.form_submit_button("Simpan Pembayaran"):
            pk, ph = min(n, 15000), max(0, n-15000)
            sh.worksheet("Pemasukan").append_row([datetime.now().strftime("%d/%m/%Y"), w, t, b, n, pk, ph, "LUNAS"])
            st.success("Tersimpan!"); st.cache_data.clear(); st.rerun()

elif menu == "🎭 Event & Iuran":
    with st.form("f_ev"):
        ev_ada = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
        ev_p = st.selectbox("Event", ["-- Baru --"] + ev_ada)
        ev_n = st.text_input("Ketik Nama Event Baru") if ev_p == "-- Baru --" else ev_p
        w_e, j_e = st.selectbox("Warga", sorted(df_warga['Nama'].tolist())), st.number_input("Jumlah Iuran", step=5000)
        if st.form_submit_button("Simpan Iuran"):
            sh.worksheet("Event").append_row([datetime.now().strftime("%d/%m/%Y"), w_e, ev_n, j_e])
            st.success("Berhasil!"); st.cache_data.clear(); st.rerun()

elif menu == "📤 Pengeluaran":
    with st.form("f_out"):
        kat = st.selectbox("Kategori Dana", ["Kas", "Hadiah", "Event"])
        ev_list = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
        ev_ref = st.selectbox("Pilih Event (Wajib jika Kategori Event)", ["N/A"] + ev_list)
        nom, ket = st.number_input("Nominal"), st.text_input("Keterangan Barang/Jasa")
        if st.form_submit_button("Catat Pengeluaran"):
            final_ket = f"[{ev_ref}] {ket}" if kat == "Event" else ket
            sh.worksheet("Pengeluaran").append_row([datetime.now().strftime("%d/%m/%Y"), kat, nom, final_ket])
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
    st.dataframe(df_masuk.tail(20), use_container_width=True)
