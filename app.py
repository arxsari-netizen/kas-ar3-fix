import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import re

# --- 1. CONFIG ---
st.set_page_config(page_title="AR-ROYHAAN 3", layout="wide",initial_sidebar_state="expanded")
st.markdown("""
    <style>
        [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        .stApp { background-color: #f8f9fa; } 
        [data-testid="stMetric"] { background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px; }
        button[kind="headerNoPadding"] { visibility: visible !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': 'user'})

# --- 3. DATA ENGINE ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

# --- 🔥 FUNGSI LOG GLOBAL ---
def log_duit(jenis, aksi, nominal, ket):
    try:
        waktu = datetime.now().strftime("%d/%m/%Y %H:%M")
        user = st.session_state.get('role', 'user').upper()
        sh.worksheet("Log_Keuangan").append_row([waktu, user, jenis, aksi, int(nominal), ket])
    except: pass

def log_inv(aksi, nama, detail):
    try:
        waktu = datetime.now().strftime("%d/%m/%Y %H:%M")
        user = st.session_state.get('role', 'user').upper()
        sh.worksheet("Log_Inventaris").append_row([waktu, user, aksi, nama, detail])
    except: pass

@st.cache_data(ttl=30)
def load_data(sheet_name):
    try:
        ws = sh.worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun', 'Dipinjam']
        for col in cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

df_masuk, df_keluar, df_warga, df_event = load_data("Pemasukan"), load_data("Pengeluaran"), load_data("Warga"), load_data("Event")
df_inv, df_pus = load_data("Inventaris"), load_data("Pustaka")

def gdrive_fix(url):
    try:
        if '/d/' in url: return f"https://drive.google.com/uc?export=open&id={url.split('/d/')[1].split('/')[0]}"
        elif 'id=' in url: return f"https://drive.google.com/uc?export=open&id={url.split('id=')[1].split('&')[0]}"
        return url
    except: return url

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("""
        <div style="text-align: left;">
            <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="80">
            <p style="font-size: 9px; color: #666; font-style: italic; margin-top: -5px;">"We come to learn & bring science back"</p>
            <hr style="margin-top: 10px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
        </div>
    """, unsafe_allow_html=True)

    if st.session_state['logged_in']:
        st.markdown(f"**🔓 {st.session_state['role'].upper()}**")
        if st.button("Log Out ➔"):
            st.session_state.update({'logged_in': False, 'role': 'user'})
            st.rerun()
    else:
        with st.expander("🔒 Login Admin"):
            with st.form("login_admin"):
                u, p = st.text_input("Username"), st.text_input("Password", type="password")
                if st.form_submit_button("Masuk"):
                    if u == st.secrets["users"]["admin_user"] and p == st.secrets["users"]["admin_password"]:
                        st.session_state.update({"logged_in": True, "role": "admin"})
                        st.rerun()
                    else: st.error("Akses Ditolak!")

    list_menu = ["📊 Laporan", "📚 Pustaka", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📦 Inventaris", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📚 Pustaka", "📦 Inventaris", "📜 Log"]
    menu = st.radio("NAVIGASI", list_menu)

# --- 5. DASHBOARD CALCULATIONS ---
in_k, in_h, in_e = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum(), df_event['Jumlah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
out_e = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

st.title(f"{menu}")
if (st.session_state['role'] == "admin" and menu not in ["📦 Inventaris", "📚 Pustaka"]) or (menu == "📊 Laporan"):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 SALDO KAS", f"Rp {int(in_k - out_k):,}")
    m2.metric("🎁 SALDO HADIAH", f"Rp {int(in_h - out_h):,}")
    m3.metric("🎭 SALDO EVENT", f"Rp {int(in_e - out_e):,}")
    m4.metric("🏧 TOTAL TUNAI", f"Rp {int((in_k+in_h+in_e)-(out_k+out_h+out_e)):,}")
    st.divider()

# --- 6. MENU LOGIC ---
bln_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

if menu == "📚 Pustaka":
    if st.session_state['role'] == "admin":
        with st.expander("➕ Tambah Materi Baru"):
            with st.form("f_add_pus", clear_on_submit=True):
                j_p, k_p = st.text_input("Judul"), st.selectbox("Kategori", ["Kitab", "Rekaman Audio", "Video", "Foto", "Dokumen"])
                l_p, t_p = st.text_input("URL"), st.selectbox("Tipe", ["PDF", "Gambar", "Audio", "Link/Video"])
                d_p = st.text_area("Deskripsi")
                if st.form_submit_button("Simpan"):
                    sh.worksheet("Pustaka").append_row([j_p, k_p, l_p, t_p, d_p])
                    log_inv("TAMBAH PUSTAKA", j_p, k_p)
                    st.success("Tersimpan!"); st.cache_data.clear(); time.sleep(1); st.rerun()

    if not df_pus.empty:
        sel_k = st.selectbox("📂 Filter", ["Semua"] + df_pus['Kategori'].unique().tolist())
        df_view = df_pus if sel_k == "Semua" else df_pus[df_pus['Kategori'] == sel_k]
        for _, row in df_view.iterrows():
            with st.container():
                st.write(f"### {row['Judul']}")
                st.caption(f"{row['Kategori']} | {row['Tipe']}")
                st.write(row['Deskripsi'])
                if row['Tipe'] == "PDF": st.link_button("📖 Buka PDF", row['Link'])
                st.divider()

elif menu == "📊 Laporan":
    t1, t2, t3 = st.tabs(["💰 Rekap Bulanan", "🎭 Detail Event", "📤 Riwayat"])
    with t1:
        thn = st.selectbox("Pilih Tahun", range(2022, 2031), index=4)
        df_y = df_masuk[df_masuk['Tahun'] == thn].copy()
        if not df_y.empty:
            p_kas = df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0).astype(int)
            st.write("#### 🟢 Tabel Kas"); st.dataframe(p_kas, use_container_width=True)

elif menu == "📦 Inventaris":
    tab_view, tab_add, tab_edit = st.tabs(["📋 Daftar", "➕ Tambah", "🔄 Update"])
    with tab_view:
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    with tab_add:
        if st.session_state['role'] == "admin":
            with st.form("f_inv_add"):
                nb, sp, jml, lok = st.text_input("Nama"), st.text_input("Spek"), st.number_input("Stok", 1), st.text_input("Lokasi")
                if st.form_submit_button("Simpan"):
                    sh.worksheet("Inventaris").append_row([nb, sp, int(jml), lok, "Baik", "Tersedia", 0, "-"])
                    log_inv("TAMBAH ASET", nb, f"Jumlah: {jml}")
                    st.success("Tersimpan!"); st.cache_data.clear(); time.sleep(1); st.rerun()
    with tab_edit:
        if st.session_state['role'] == "admin" and not df_inv.empty:
            with st.form("f_inv_upd"):
                b_edit = st.selectbox("Pilih Barang", df_inv['Nama Barang'].tolist())
                curr = df_inv[df_inv['Nama Barang'] == b_edit].iloc[0]
                n_dipinjam = st.number_input("Dipinjam", 0, int(curr['Jumlah']), int(curr['Dipinjam']))
                n_lok = st.text_input("Lokasi", value=curr['Lokasi'])
                if st.form_submit_button("Update"):
                    rows = sh.worksheet("Inventaris").get_all_records()
                    r_idx = next((i + 2 for i, r in enumerate(rows) if r['Nama Barang'] == b_edit), 0)
                    if r_idx:
                        sh.worksheet("Inventaris").update_cell(r_idx, 7, n_dipinjam)
                        sh.worksheet("Inventaris").update_cell(r_idx, 4, n_lok)
                        log_inv("UPDATE", b_edit, f"Pinjam: {n_dipinjam}, Lok: {n_lok}")
                        st.success("Updated!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "📥 Kas Bulanan" and st.session_state['role'] == "admin":
    w_pilih = st.selectbox("Warga", sorted(df_warga['Nama'].tolist()))
    mode = st.radio("Mode", ["Paket Lengkap (50rb)", "Hanya Kas (15rb)", "Hanya Hadiah (35rb)"], horizontal=True)
    with st.form("f_kas"):
        n = st.number_input("Nominal", value=50000 if "Paket" in mode else 15000)
        t_in, b_in = st.selectbox("Tahun", range(2022, 2031), index=4), st.selectbox("Bulan", bln_list)
        if st.form_submit_button("Simpan"):
            # Looping Alokasi
            sh.worksheet("Pemasukan").append_row([datetime.now().strftime("%d/%m/%Y"), w_pilih, t_in, b_in, n, n, 0, "LUNAS", mode])
            log_duit("RUTIN", "MASUK", n, f"Iuran {w_pilih} ({b_in} {t_in})")
            st.success("Berhasil!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "📤 Pengeluaran" and st.session_state['role'] == "admin":
    kat = st.radio("Sumber", ["Kas", "Hadiah", "Event"], horizontal=True)
    with st.form("f_out"):
        nom, ket = st.number_input("Nominal", 0), st.text_input("Ket")
        if st.form_submit_button("Simpan"):
            sh.worksheet("Pengeluaran").append_row([datetime.now().strftime("%d/%m/%Y"), kat, nom, ket])
            log_duit(kat.upper(), "KELUAR", nom, ket)
            st.success("Tercatat!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "📜 Log":
    t_k, t_i = st.tabs(["💰 Keuangan", "📦 Inventaris"])
    with t_k:
        df_lk = pd.DataFrame(sh.worksheet("Log_Keuangan").get_all_records()).iloc[::-1]
        st.dataframe(df_lk.head(50), use_container_width=True, hide_index=True)
    with t_i:
        df_li = pd.DataFrame(sh.worksheet("Log_Inventaris").get_all_records()).iloc[::-1]
        st.dataframe(df_li.head(50), use_container_width=True, hide_index=True)
