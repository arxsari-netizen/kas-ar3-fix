import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import re

# --- 1. CONFIG ---
st.set_page_config(page_title="AR-ROYHAAN 3", layout="wide")
st.markdown("""<style>header {visibility: hidden;} .stApp { background-color: #f8f9fa; } [data-testid="stMetric"] { background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px; }</style>""", unsafe_allow_html=True)

# --- 2. SESSION STATE (Default: Warga/User) ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': 'user'})

# --- 3. DATA ENGINE ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=30)
def load_data(sheet_name):
    try:
        ws = sh.worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
        for col in cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame()

df_masuk, df_keluar, df_warga, df_event = load_data("Pemasukan"), load_data("Pengeluaran"), load_data("Warga"), load_data("Event")
df_inv, df_pus = load_data("Inventaris"), load_data("Pustaka")

def gdrive_fix(url):
    file_id = ""
    try:
        if '/d/' in url: file_id = url.split('/d/')[1].split('/')[0]
        elif 'id=' in url: file_id = url.split('id=')[1].split('&')[0]
        if file_id: return f"https://drive.google.com/uc?export=open&id={file_id}"
        return url
    except: return url

# --- 4. SIDEBAR (Login Admin Diselipkan di Sini) ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=80)
    
    # Bagian Login/Logout Admin
    if st.session_state['logged_in']:
        st.success(f"🔓 MODE: {st.session_state['role'].upper()}")
        if st.button("Log Out"):
            st.session_state.update({'logged_in': False, 'role': 'user'})
            st.rerun()
    else:
        st.info("🔒 MODE: WARGA (Read-Only)")
        with st.expander("Masuk sebagai Admin"):
            with st.form("login_admin"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk"):
                    if u == st.secrets["users"]["admin_user"] and p == st.secrets["users"]["admin_password"]:
                        st.session_state.update({"logged_in": True, "role": "admin"})
                        st.rerun()
                    else:
                        st.error("Akses Ditolak!")

    # Menu Navigasi
    if st.session_state['role'] == "admin":
        list_menu = ["📊 Laporan", "📚 Pustaka", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📦 Inventaris", "📜 Log"]
    else:
        list_menu = ["📊 Laporan", "📚 Pustaka", "📦 Inventaris", "📜 Log"]
    
    menu = st.radio("NAVIGASI", list_menu)

# --- 5. LOGIKA IKON ---
ikon_bunga = {"📊 Laporan": "🌸", "📚 Pustaka": "🎁", "📥 Kas Bulanan": "🌻", "🎭 Event & Iuran": "🌺", "📤 Pengeluaran": "🍂", "👥 Kelola Warga": "🌷", "📦 Inventaris": "🌵", "📜 Log": "🍃"}
ikon_aktif = ikon_bunga.get(menu, "🌼")
st.title(f"{ikon_aktif} {menu}")

# Hitung saldo global
in_k, in_h, in_e = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum(), df_event['Jumlah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
out_e = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

# Dashboard Saldo (Muncul untuk Warga di menu Laporan, atau Admin di mana saja kecuali Inv/Pustaka)
show_dashboard = (st.session_state['role'] == "admin" and menu not in ["📦 Inventaris", "📚 Pustaka"]) or \
                 (st.session_state['role'] == "user" and menu == "📊 Laporan")

if show_dashboard:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 SALDO KAS", f"Rp {int(in_k - out_k):,}")
    m2.metric("🎁 SALDO HADIAH", f"Rp {int(in_h - out_h):,}")
    m3.metric("🎭 SALDO EVENT", f"Rp {int(in_e - out_e):,}")
    m4.metric("🏧 TOTAL TUNAI", f"Rp {int((in_k+in_h+in_e)-(out_k+out_h+out_e)):,}")
    st.divider()
    
    if menu == "📊 Laporan":
       with st.expander("📢 Bagikan Laporan ke Grup"):
            sk, shd = int(in_k - out_k), int(in_h - out_h)
            pesan_wa = (f"📢 *LAPORAN KAS AR-ROYHAAN 3* \n📅 _Update: {datetime.now().strftime('%d/%m/%Y')}_\n\n*Saldo Kas:* Rp {sk:,}\n*Saldo Hadiah:* Rp {shd:,}\n━━━━━━━━━━━━━━━━━━\n*TOTAL DANA: Rp {sk+shd:,}*\n\nSyukron jazakumullah khair. 🙏")
            p_enc = pesan_wa.replace(' ', '%20').replace('\n', '%0A')
            st.link_button("📲 Kirim Laporan Kas ke WA", f"https://wa.me/?text={p_enc}")

# --- 6. MENU LOGIC ---
bln_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

if menu == "📚 Pustaka":
    st.subheader("📚 Pustaka Digital & Materi Kajian")
    if st.session_state['role'] == "admin":
        with st.expander("➕ Tambah Materi Baru"):
            with st.form("f_add_pus", clear_on_submit=True):
                j_p, k_p = st.text_input("Judul Materi"), st.selectbox("Kategori", ["Kitab", "Rekaman Audio", "Video", "Foto Kegiatan", "Dokumen"])
                l_p, t_p = st.text_input("Link G-Drive/URL"), st.selectbox("Tipe File", ["PDF", "Gambar", "Audio", "Link/Video"])
                d_p = st.text_area("Deskripsi Singkat")
                if st.form_submit_button("Simpan"):
                    sh.worksheet("Pustaka").append_row([j_p, k_p, l_p, t_p, d_p])
                    st.success("Materi Terunggah!"); st.cache_data.clear(); time.sleep(1); st.rerun()

    if not df_pus.empty:
        c_search, c_filter = st.columns([2, 1])
        cari = c_search.text_input("🔍 Cari Materi", placeholder="Contoh: doa mandi")
        sel_k = c_filter.selectbox("📂 Filter Kategori", ["Semua"] + df_pus['Kategori'].unique().tolist())
        df_view = df_pus.copy()
        if sel_k != "Semua": df_view = df_view[df_view['Kategori'] == sel_k]
        if cari:
            mask = df_view.apply(lambda row: cari.lower() in row['Judul'].lower() or cari.lower() in row['Deskripsi'].lower(), axis=1)
            df_view = df_view[mask]
        
        st.divider()
        for _, row in df_view.iterrows():
            with st.container():
                col1, col2 = st.columns([1, 4])
                icon = "📄" if row['Tipe'] == "PDF" else "🖼️" if row['Tipe'] == "Gambar" else "🔊" if row['Tipe'] == "Audio" else "🔗"
                col1.markdown(f"<h1 style='text-align: center;'>{icon}</h1>", unsafe_allow_html=True)
                col2.write(f"### {row['Judul']}")
                col2.caption(f"Kategori: {row['Kategori']} | Tipe: {row['Tipe']}")
                col2.write(row['Deskripsi'])
                with col2.expander("Lihat / Putar Materi"):
                    if row['Tipe'] == "Audio":
                        # Khusus Audio Pakai Iframe Preview
                        p_url = row['Link'].replace('/view', '/preview') if '/view' in row['Link'] else row['Link']
                        st.markdown(f'<iframe src="{p_url}" width="100%" height="150" style="border:none; border-radius:10px;"></iframe>', unsafe_allow_html=True)
                        st.link_button("🚀 Putar di G-Drive", row['Link'])
                    elif row['Tipe'] == "PDF":
                        st.markdown(f'<iframe src="{gdrive_fix(row["Link"])}" width="100%" height="500px"></iframe>', unsafe_allow_html=True)
                    elif row['Tipe'] == "Gambar":
                        st.image(gdrive_fix(row['Link']), use_container_width=True)
                    else: st.link_button("Buka Materi Luar", row['Link'])
            st.divider()

elif menu == "📊 Laporan":
    t1, t2, t3 = st.tabs(["💰 Rekap Bulanan", "🎭 Detail Event", "📤 Riwayat Pengeluaran"])
    with t1:
        thn = st.selectbox("Tahun", range(2022, 2031), index=4)
        df_y = df_masuk[df_masuk['Tahun'] == thn]
        if not df_y.empty:
            st.write("#### 🟢 Kas (15rb)"); st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0).astype(int), use_container_width=True)
            st.write("#### 🟡 Hadiah (35rb)"); st.dataframe(df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0).astype(int), use_container_width=True)
    with t2:
        if not df_event.empty:
            ev_sel = st.selectbox("Pilih Event", df_event['Nama Event'].unique())
            e_in = df_event[df_event['Nama Event'] == ev_sel]['Jumlah'].sum()
            e_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(f"[{ev_sel}]"))]['Jumlah'].sum()
            st.metric("Sisa Dana Event", f"Rp {int(e_in - e_out):,}")
            st.dataframe(df_event[df_event['Nama Event'] == ev_sel][['Tanggal', 'Nama', 'Jumlah']], hide_index=True)
    with t3:
        ck, ch = st.columns(2)
        ck.write("#### 📤 Pengeluaran KAS"); ck.dataframe(df_keluar[df_keluar['Kategori'] == 'Kas'][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True)
        ch.write("#### 📤 Pengeluaran HADIAH"); ch.dataframe(df_keluar[df_keluar['Kategori'] == 'Hadiah'][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True)

elif menu == "📦 Inventaris":
    tab_view, tab_add, tab_edit = st.tabs(["📋 Daftar", "➕ Tambah", "✏️ Update"])
    with tab_view:
        if not df_inv.empty:
            st.dataframe(df_inv, hide_index=True, use_container_width=True)
            # Share WA Logic
            lb, lr, lp = df_inv[df_inv['Kondisi'] == 'Baik']['Nama Barang'].tolist(), df_inv[df_inv['Kondisi'] != 'Baik']['Nama Barang'].tolist(), df_inv[df_inv['Status'] == 'Dipinjam']['Nama Barang'].tolist()
            p_inv = f"📦 *LAPORAN ASET AR-ROYHAAN 3*\n📅 _Update: {datetime.now().strftime('%d/%m/%Y')}_\n\n✅ *BARANG LAYAK:* {', '.join(lb) if lb else '-'}\n\n⚠️ *RUSAK:* {', '.join(lr) if lr else '-'}\n\n📢 *DIPINJAM:* {', '.join(lp) if lp else 'Semua Tersedia'}\n\nSyukron. ✨"
            st.link_button("📲 Share Detail Aset ke WA", f"https://wa.me/?text={p_inv.replace(' ', '%20').replace('\n', '%0A')}")

    if st.session_state['role'] == "admin":
        with tab_add:
            with st.form("f_inv_add", clear_on_submit=True):
                nb, sp, jml, lok = st.text_input("Nama Barang"), st.text_input("Spesifikasi"), st.number_input("Jumlah", min_value=1), st.text_input("Lokasi")
                kon, sts = st.selectbox("Kondisi", ["Baik", "Rusak Ringan", "Rusak Parah"]), st.selectbox("Status", ["Tersedia", "Dipinjam", "Hilang"])
                if st.form_submit_button("Simpan"):
                    sh.worksheet("Inventaris").append_row([nb, sp, int(jml), lok, kon, sts])
                    st.success("Tersimpan!"); st.cache_data.clear(); time.sleep(1); st.rerun()
        with tab_edit:
            if not df_inv.empty:
                with st.form("f_inv_edit"):
                    b_edit = st.selectbox("Pilih Barang", df_inv['Nama Barang'].tolist())
                    n_lok, n_k, n_s = st.text_input("Update Lokasi"), st.selectbox("Kondisi Baru", ["Baik", "Rusak"]), st.selectbox("Status Baru", ["Tersedia", "Dipinjam"])
                    if st.form_submit_button("Update"):
                        r = sh.worksheet("Inventaris").find(b_edit).row
                        if n_lok: sh.worksheet("Inventaris").update_cell(r, 4, n_lok)
                        sh.worksheet("Inventaris").update_cell(r, 5, n_k); sh.worksheet("Inventaris").update_cell(r, 6, n_s)
                        st.success("Updated!"); st.cache_data.clear(); time.sleep(1); st.rerun()
    else:
        with tab_add: st.warning("Khusus Admin")
        with tab_edit: st.warning("Khusus Admin")

# --- MENU KHUSUS ADMIN ---
elif menu == "📥 Kas Bulanan" and st.session_state['role'] == "admin":
    w_pilih = st.selectbox("Nama Warga", sorted(df_warga['Nama'].tolist()))
    with st.form("f_kas", clear_on_submit=True):
        n = st.number_input("Nominal", step=5000)
        t, b = st.selectbox("Tahun", range(2022, 2031), index=4), st.selectbox("Bulan", bln_list)
        if st.form_submit_button("Simpan"):
            pk, ph = (min(n, 15000), max(0, n-15000))
            sh.worksheet("Pemasukan").append_row([datetime.now().strftime("%d/%m/%Y"), w_pilih, t, b, int(n), int(pk), int(ph), "LUNAS"])
            st.success("OK!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "📤 Pengeluaran" and st.session_state['role'] == "admin":
    kat_pilih = st.radio("Sumber Dana:", ["Kas", "Hadiah", "Event"], horizontal=True)
    with st.form("f_out", clear_on_submit=True):
        ev_ref = st.selectbox("Event:", ["N/A"] + (df_event['Nama Event'].unique().tolist() if not df_event.empty else [])) if kat_pilih == "Event" else "N/A"
        nom, ket = st.number_input("Nominal", min_value=0), st.text_input("Keterangan")
        if st.form_submit_button("Simpan"):
            sh.worksheet("Pengeluaran").append_row([datetime.now().strftime("%d/%m/%Y"), kat_pilih, int(nom), f"[{ev_ref}] {ket}" if kat_pilih == "Event" else ket])
            st.success("Tercatat!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "👥 Kelola Warga" and st.session_state['role'] == "admin":
    st.dataframe(df_warga[['Nama', 'Role']], hide_index=True, use_container_width=True)
    with st.form("t_w"):
        nw, nr = st.text_input("Nama"), st.selectbox("Role", ["Main Warga", "Warga Support"])
        if st.form_submit_button("Tambah"): sh.worksheet("Warga").append_row([nw, nr]); st.cache_data.clear(); st.rerun()

elif menu == "🎭 Event & Iuran" and st.session_state['role'] == "admin":
    with st.form("f_ev", clear_on_submit=True):
        ev_p = st.selectbox("Event", ["-- Baru --"] + (df_event['Nama Event'].unique().tolist() if not df_event.empty else []))
        ev_n = st.text_input("Nama Event Baru") if ev_p == "-- Baru --" else ev_p
        w_e, j_e = st.selectbox("Warga", sorted(df_warga['Nama'].tolist())), st.number_input("Jumlah", step=5000)
        if st.form_submit_button("Simpan"):
            sh.worksheet("Event").append_row([datetime.now().strftime("%d/%m/%Y"), w_e, ev_n, int(j_e)])
            st.success("OK!"); st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "📜 Log":
    st.dataframe(df_masuk.tail(20), hide_index=True, use_container_width=True)
