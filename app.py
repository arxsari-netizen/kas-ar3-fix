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
        /* Sembunyikan garis pelangi di paling atas tapi biarkan tombol sidebar ada */
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0);
        }
        .stApp { background-color: #f8f9fa; } 
        [data-testid="stMetric"] { background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px; }
        
        /* CSS Tambahan biar tombol sidebar tetep kelihatan meski header transparan */
        button[kind="headerNoPadding"] {
            visibility: visible !important;
        }
    </style>
""", unsafe_allow_html=True)

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
# --- UPDATE POSISI FILTER WARGA DI SINI ---
# Kita buat list nama warga yang STATUS-nya 'Aktif' atau 'Non-Warga' saja
# Biar Alumni (Pahmi) nggak muncul di pilihan input baru
if not df_warga.empty:
    # Cek dulu apakah kolom 'Status' ada di Google Sheets, kalau nggak ada kita default ke 'Aktif'
    if 'Status' not in df_warga.columns:
        df_warga['Status'] = 'Aktif'
    
    # List untuk dropdown input (Hanya yang Aktif & Non-Warga)
    df_aktif = df_warga[df_warga['Status'].isin(['Aktif', 'Non-Warga'])]
    list_warga_input = sorted(df_aktif['Nama'].tolist())
else:
    list_warga_input = []
def get_row_index(worksheet, nama, kriteria_kedua=None, role=None):
    data = worksheet.get_all_values()
    for i, row in enumerate(data):
        # Cari Warga (Nama di Kolom 1, Role di Kolom 2)
        if role is not None:
            if row[0] == nama and row[1] == role:
                return i + 1
        # Cari Inventaris (Nama di Kolom 1, Lokasi di Kolom 4)
        elif kriteria_kedua is not None:
            if len(row) >= 4:
                if row[0] == nama and row[3] == kriteria_kedua:
                    return i + 1
    return None
def gdrive_fix(url):
    file_id = ""
    try:
        if '/d/' in url: file_id = url.split('/d/')[1].split('/')[0]
        elif 'id=' in url: file_id = url.split('id=')[1].split('&')[0]
        if file_id: return f"https://drive.google.com/uc?export=open&id={file_id}"
        return url
    except: return url
def get_sisa_piutang():
    try:
        df_t = load_data("Talangan")
        if df_t.empty:
            return pd.DataFrame(columns=['Nama', 'Sisa Utang', 'Keterangan Terakhir'])
        
        # Hitung Amount
        df_t['Amount'] = df_t.apply(lambda x: x['Nominal'] if x['Tipe'] == 'PINJAM' else -x['Nominal'], axis=1)
        
        # Kelompokkan berdasarkan Nama
        summary = df_t.groupby('Nama').agg({
            'Amount': 'sum',
            'Keterangan': 'last' # Ambil keterangan dari transaksi terakhir
        }).reset_index()
        
        summary.columns = ['Nama', 'Sisa Utang', 'Keterangan Terakhir']
        
        # Filter yang utangnya masih > 0
        return summary[summary['Sisa Utang'] > 0]
    except:
        return pd.DataFrame(columns=['Nama', 'Sisa Utang', 'Keterangan Terakhir'])
# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown(f"""
        <div style="text-align: left;">
            <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="80" style="margin-bottom: 0px;">
            <p style="font-size: 9px; color: #666; font-style: italic; margin-top: -5px; margin-bottom: 0px;">
                "We come to learn & bring science back"
            </p>
            <hr style="margin-top: 10px; margin-bottom: 15px; border: 0; border-top: 1px solid #ddd;">
        </div>
    """, unsafe_allow_html=True)

    if st.session_state['logged_in']:
        st.markdown("""
            <style>
                div[data-testid="stSidebar"] div.stButton button {
                    display: inline-flex;
                    padding: 0px 10px !important;
                    height: 24px !important;
                    min-height: 24px !important;
                    width: auto !important;
                    font-size: 11px !important;
                    margin-top: -5px !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="margin-bottom: 5px;">
                <span style="font-size: 12px; font-weight: bold; color: #4CAF50; margin-right: 10px;">🔓 {st.session_state['role'].upper()}</span>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Log Out ➔", key="btn_out"):
            st.session_state.update({'logged_in': False, 'role': 'user'})
            st.rerun()
    else:
        st.caption("🔒 **WARGA (Read-Only)**")
        with st.expander("Login Admin"):
            with st.form("login_admin"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk"):
                    if u == st.secrets["users"]["admin_user"] and p == st.secrets["users"]["admin_password"]:
                        st.session_state.update({"logged_in": True, "role": "admin"})
                        st.rerun()
                    elif u == st.secrets["users"]["event_user"] and p == st.secrets["users"]["event_password"]:
                        st.session_state.update({"logged_in": True, "role": "event_manager"})
                        st.rerun()
                    else:
                        st.error("Akses Ditolak!")

    if st.session_state['role'] == "admin":
        list_menu = ["📊 Laporan", "📚 Pustaka", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📦 Inventaris", "💸 Dana Talangan", "📜 Log"]
    elif st.session_state['role'] == "event_manager":
        list_menu = ["📊 Laporan", "🎭 Event & Iuran", "📤 Pengeluaran"]
    else:
        list_menu = ["📊 Laporan", "📚 Pustaka", "📦 Inventaris", "📜 Log"]
    
    menu = st.radio("NAVIGASI", list_menu)

# --- 5. LOGIKA DISPLAY ---
st.title(f"{menu}")

in_k, in_h, in_e = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum(), df_event['Jumlah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
out_e = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()
# Tambahkan ini setelah perhitungan out_e
df_p = get_sisa_piutang()
total_piutang = df_p['Sisa Utang'].sum() if not df_p.empty else 0
show_dashboard = (st.session_state['role'] in ["admin", "event_manager"] and menu not in ["📦 Inventaris", "📚 Pustaka"]) or \
                 (st.session_state['role'] == "user" and menu == "📊 Laporan")

if show_dashboard:
    m1, m2, m3, m4 = st.columns(4)
    
    # 4. TAMPILKAN METRIK
    # Kas dikurangi piutang agar jadi angka "jujur"
    m1.metric("💰 SALDO KAS", f"Rp {int(in_k - out_k - total_piutang):,}")
    m2.metric("🎁 SALDO HADIAH", f"Rp {int(in_h - out_h):,}")
    m3.metric("🎭 SALDO EVENT", f"Rp {int(in_e - out_e):,}")
    
    # Uang Fisik = Total (In - Out) - Piutang
    uang_fisik = (in_k + in_h + in_e) - (out_k + out_h + out_e) - total_piutang
    m4.metric("🏧 UANG FISIK (Di Tangan)", f"Rp {int(uang_fisik):,}")
    
    # 5. KHUSUS ADMIN
    if st.session_state['role'] == "admin":
        st.divider()
        c_admin = st.columns(4)
        c_admin[0].metric("💸 PIUTANG AKTIF", f"Rp {int(total_piutang):,}")
    
    if menu == "📊 Laporan":
       with st.expander("📢 Bagikan Laporan ke Grup"):
            sk, shd = int(in_k - out_k), int(in_h - out_h)
            pesan_wa = (f"📢 *LAPORAN KAS AR-ROYHAAN 3*\n📅 _Update: {datetime.now().strftime('%d/%m/%Y')}_\n\n*Saldo Kas:* Rp {sk:,}\n*Saldo Hadiah:* Rp {shd:,}\n━━━━━━━━━━━━━━━━━━\n*TOTAL DANA: Rp {sk+shd:,}*\n\nSyukron jazakumullah khair. 🙏")
            p_enc = pesan_wa.replace(' ', '%20').replace('\n', '%0A')
            st.link_button("📲 Kirim Laporan Kas ke WA", f"https://wa.me/?text={p_enc}")

# --- 6. MENU LOGIC ---
bln_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

if menu == "📚 Pustaka":
    st.subheader("Selamat datang di Pustaka")
    st.markdown("Tempat Mencari serpihan ilmu dan kenangan")
    if st.session_state['role'] == "admin":
        with st.expander("➕ Tambah Materi Baru"):
            with st.form("f_add_pus", clear_on_submit=True):
                j_p, k_p = st.text_input("Judul Materi"), st.selectbox("Kategori", ["Kitab", "Rekaman Audio", "Video", "Foto Kegiatan", "Dokumen"])
                l_p, t_p = st.text_input("Link G-Drive/URL"), st.selectbox("Tipe File", ["PDF", "Gambar", "Foto", "Video", "Audio", "Link"])
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
        # 1. PISAH DATA: Galeri (Foto/Video) vs Pustaka (PDF/Audio/Lainnya)
        # Sekarang Galeri fokus ke Tipe "Foto" atau "Video"
        galeri_df = df_view[df_view['Tipe'].isin(["Foto", "Video"])]
        pustaka_df = df_view[~df_view['Tipe'].isin(["Foto", "Video"])]

        # 2. TAMPILKAN GALERI (Berbasis Selectbox Filter)
        if not galeri_df.empty:
            st.subheader("📸 Galeri Kegiatan")
            
            # Ambil daftar kegiatan unik
            list_kegiatan = ["--Pilih--"] + galeri_df['Kegiatan'].unique().tolist()
            
            # Selectbox sebagai navigasi utama galeri
            pilih_kegiatan = st.selectbox("Pilih Kegiatan", list_kegiatan)
            
            # Filter data berdasarkan pilihan
            tampilan_foto = galeri_df[galeri_df['Kegiatan'] == pilih_kegiatan]
            
            # Tampilkan dalam grid 3 kolom
            cols = st.columns(3)
            for i, (_, row) in enumerate(tampilan_foto.iterrows()):
                with cols[i % 3]:
                    # Logika Thumbnail
                    url_g = row['Link']
                    file_id = url_g.split('/d/')[1].split('/')[0] if '/d/' in url_g else (url_g.split('id=')[1].split('&')[0] if 'id=' in url_g else "")
                    if file_id:
                        st.image(f"https://drive.google.com/thumbnail?id={file_id}&sz=w600", use_container_width=True)
                    st.caption(row['Judul'])
            st.divider()

        # 3. TAMPILKAN PUSTAKA (List)
        if not pustaka_df.empty:
            st.subheader("📚 Pustaka Digital")
            for _, row in pustaka_df.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    # Icon sesuai Tipe
                    icon = "📄" if row['Tipe'] == "PDF" else "🖼️" if row['Tipe'] == "Gambar" else "🔊" if row['Tipe'] == "Audio" else "🔗"
                    col1.markdown(f"<h1 style='text-align: center;'>{icon}</h1>", unsafe_allow_html=True)
                    col2.write(f"### {row['Judul']}")
                    col2.caption(f"Kategori: {row['Kategori']} | Tipe: {row['Tipe']}")
                    col2.write(row['Deskripsi'])
                    with col2.expander("Lihat / Putar Materi"):
                        # ... (isi expander biarkan sama seperti kode asli lo) ...
                        if row['Tipe'] == "Audio":
                            p_url = row['Link'].replace('/view', '/preview') if '/view' in row['Link'] else row['Link']
                            st.markdown(f'<iframe src="{p_url}" width="100%" height="150" style="border:none; border-radius:10px;"></iframe>', unsafe_allow_html=True)
                            st.link_button("🚀 Putar di G-Drive", row['Link'])
                        elif row['Tipe'] == "PDF":
                            st.markdown(f'<iframe src="{gdrive_fix(row["Link"])}" width="100%" height="500px"></iframe>', unsafe_allow_html=True)
                        elif row['Tipe'] == "Gambar":
                            # ... (logika gambar lo yang lama) ...
                            url_g = row['Link']
                            file_id = url_g.split('/d/')[1].split('/')[0] if '/d/' in url_g else (url_g.split('id=')[1].split('&')[0] if 'id=' in url_g else "")
                            if file_id: st.image(f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000", use_container_width=True)
                            st.link_button("📂 Buka Gambar Asli", row['Link'])
                st.divider()
elif menu == "📊 Laporan":
    t1, t2, t3 = st.tabs(["💰 Rekap Bulanan", "🎭 Detail Event", "📤 Riwayat Pengeluaran"])
    with t1:
        thn = st.selectbox("Pilih Tahun Laporan", range(2022, 2031), index=4)
        df_y = df_masuk[df_masuk['Tahun'] == thn].copy()
        
        if not df_y.empty and not df_warga.empty:
            df_y = df_y.merge(df_warga[['Nama', 'Role']], on='Nama', how='left')
            df_y['Bulan'] = pd.Categorical(df_y['Bulan'], categories=bln_list, ordered=True)

            def warna_iuran(df_pivot, target_nominal):
                def terapkan_style(row):
                    nama_idx = row.name
                    role = df_warga[df_warga['Nama'] == nama_idx]['Role'].values[0] if nama_idx in df_warga['Nama'].values else "Main Warga"
                    styles = []
                    for nilai in row:
                        if role == "Main Warga" and 0 < nilai < target_nominal:
                            styles.append('color: red; font-weight: bold')
                        else:
                            styles.append('color: black')
                    return styles
                return df_pivot.style.apply(terapkan_style, axis=1)

            st.write("#### 🟢 Kas (Target Main: 15rb)")
            p_kas = df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum', observed=False).fillna(0).astype(int)
            st.dataframe(warna_iuran(p_kas, 15000), use_container_width=True)
            
            st.write("#### 🟡 Hadiah (Target Main: 35rb)")
            p_had = df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum', observed=False).fillna(0).astype(int)
            st.dataframe(warna_iuran(p_had, 35000), use_container_width=True)
            st.info("💡 **Merah Bold:** Hanya berlaku untuk 'Main Warga' yang cicilannya belum mencapai target kewajiban.")
            
            # --- BAGIAN HIBAH (SUDAH DIRAPIKAN) ---
            st.divider()
            st.write("#### 🧧 Rincian Dana Hibah / Tambahan")
            df_hibah_view = df_masuk[df_masuk['Nama'] == 'HIBAH']
            
            if not df_hibah_view.empty:
                st.dataframe(
                    df_hibah_view[['Tanggal', 'Tipe', 'Kas']], 
                    column_config={"Kas": "Nominal", "Tipe": "Keterangan"},
                    hide_index=True, 
                    use_container_width=True
                )
                st.info(f"Total Dana Hibah Terkumpul: Rp {int(df_hibah_view['Kas'].sum()):,}")
            else:
                st.caption("Belum ada dana hibah yang tercatat.")
    with t2:
        if not df_event.empty:
            ev_sel = st.selectbox("Pilih Event", df_event['Nama Event'].unique())
            df_ev_masuk = df_event[df_event['Nama Event'] == ev_sel]
            df_ev_keluar = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(re.escape(ev_sel), na=False))]
            e_in, e_out = df_ev_masuk['Jumlah'].sum(), df_ev_keluar['Jumlah'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Iuran", f"Rp {int(e_in):,}"); c2.metric("Total Belanja", f"Rp {int(e_out):,}"); c3.metric("Sisa Saldo", f"Rp {int(e_in - e_out):,}")
            st.divider()
            col_in, col_out = st.columns(2)
            col_in.write("#### 📥 Pemasukan"); col_in.dataframe(df_ev_masuk[['Tanggal', 'Nama', 'Jumlah']], hide_index=True)
            col_out.write("#### 📤 Pengeluaran"); col_out.dataframe(df_ev_keluar[['Tanggal', 'Keterangan', 'Jumlah']], hide_index=True)
    with t3:
        ck, ch = st.columns(2)
        ck.write("#### 📤 Pengeluaran KAS"); ck.dataframe(df_keluar[df_keluar['Kategori'] == 'Kas'][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True)
        ch.write("#### 📤 Pengeluaran HADIAH"); ch.dataframe(df_keluar[df_keluar['Kategori'] == 'Hadiah'][['Tanggal', 'Jumlah', 'Keterangan']], hide_index=True)


# --- 8. REFACTORED INVENTARIS (The Cleanest Version) ---
elif menu == "📦 Inventaris":
    st.cache_data.clear()
    tab_view, tab_add, tab_edit = st.tabs(["📋 Daftar Aset", "➕ Tambah Baru", "🔄 Update Status"])
    ws_inv = sh.worksheet("Inventaris")
# --- TAMBAHKAN BARIS INI UNTUK MENGURUTKAN ---
    if not df_inv.empty:
        # Urutkan berdasarkan Nama Barang (A-Z), lalu Lokasi
        df_inv = df_inv.sort_values(by=['Nama Barang', 'Lokasi'], ascending=[True, True])
    # ---------------------------------------------
    with tab_view:
        if not df_inv.empty:
            # --- 1. INISIALISASI STATE BARU ---
            if 'cart' not in st.session_state:
                st.session_state['cart'] = {}
            if 'reset_cnt' not in st.session_state:
                st.session_state['reset_cnt'] = 0

            st.markdown("### 📋 Pilih Barang untuk Laporan")
            
            cari_inv = st.text_input("🔍 Cari Barang...", placeholder="Ketik nama barang...")
            df_display = df_inv.copy()
            if cari_inv:
                df_display = df_display[df_display['Nama Barang'].str.contains(cari_inv, case=False)]

            cols_inv = st.columns(4) 
            
            for i, row in df_display.iterrows():
                with cols_inv[i % 4]:
                    # --- CSS UNTUK SERAGAMKAN UKURAN GAMBAR ---
                    # Kita bungkus gambar di dalam div yang tingginya dikunci (misal 150px)
                    st.markdown("""
                        <style>
                        .img-container {
                            width: 100%;
                            height: 150px; /* Kunci tinggi gambar bray */
                            object-fit: cover; /* Biar gambar auto-crop dan gak gepeng */
                            border-radius: 10px;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                    # Tampilkan Gambar
                    url_f = row['Link Foto']; f_id = ""
                    if url_f and '/d/' in url_f: f_id = url_f.split('/d/')[1].split('/')[0]
                    elif url_f and 'id=' in url_f: f_id = url_f.split('id=')[1].split('&')[0]
                    
                    if f_id:
                        img_src = f"https://drive.google.com/thumbnail?id={f_id}&sz=w400"
                    else:
                        img_src = "https://via.placeholder.com/400x300?text=No+Image"
                    
                    # Kita pake HTML tag biar CSS-nya jalan
                    st.markdown(f'<img src="{img_src}" class="img-container">', unsafe_allow_html=True)
                    
                    # --- INFO BARANG ---
                    st.markdown(f"**{row['Nama Barang']}**")
                    # 1. Cek jumlah tersedia (Stok asli dikurangi yang sedang dipinjam)
                    stok_fisik = int(row['Jumlah'])
                    sedang_pinjam = int(row['Dipinjam']) if pd.notna(row['Dipinjam']) else 0
                    stok_ready = stok_fisik - sedang_pinjam
                    
                    # 2. Siapkan info peminjam kalau ada
                    info_peminjam = ""
                    if sedang_pinjam > 0:
                        nama_peminjam = row['Keterangan'] if pd.notna(row['Keterangan']) and row['Keterangan'] != "-" else "Warga"
                        info_peminjam = f"\n| 👤 Pinjam: {sedang_pinjam} ({nama_peminjam})"

                    # 3. Tampilkan di Kartu
                    st.markdown(f"**{row['Nama Barang']}**")
                    
                    # Warna status: Merah kalau habis dipinjam, Hijau kalau ready
                    warna_stok = "green" if stok_ready > 0 else "red"
                    
                    st.markdown(f"""
                        <div style="font-size: 13px; line-height: 1.4;">
                            📍 {row['Lokasi']}<br>
                            ✅ Tersedia: <span style="color:{warna_stok}; font-weight:bold;">{stok_ready}</span> / Total: {stok_fisik}
                            <span style="color: #d63031; font-weight: 500;">{info_peminjam}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Spek di dalam expander
                    val_spec = str(row['Spesifikasi']) if 'Spesifikasi' in row and pd.notna(row['Spesifikasi']) else "-"
                    if val_spec != "-":
                        with st.expander("Lihat Spek"):
                            st.write(val_spec)
                    
                    # Input Qty
                    qty_key = f"qty_{i}_{st.session_state['reset_cnt']}"
                    qty_ambil = st.number_input("Qty", 0, int(row['Jumlah']), step=1, key=qty_key)
                    
                    if qty_ambil > 0:
                        st.session_state['cart'][i] = {
                            'nama': row['Nama Barang'], 
                            'lokasi': row['Lokasi'], 
                            'jumlah': qty_ambil,
                            'spek': val_spec
                        }
                    elif i in st.session_state['cart'] and qty_ambil == 0:
                        del st.session_state['cart'][i]

            # --- 3. GENERATE LAPORAN (DENGAN SPEK) ---
            if st.session_state['cart']:
                st.divider()
                st.markdown("### 📄 Draft Laporan Pengambilan")
                
                laporan_dict = {}
                for _, item in st.session_state['cart'].items():
                    lok = item['lokasi']
                    if lok not in laporan_dict: 
                        laporan_dict[lok] = []
                    
                    # Ambil data spek, kalau strip atau kosong gak usah ditampilin biar gak panjang
                    info_barang = f"{item['nama']} ({item['jumlah']} Unit)"
                    if item.get('spek') and item['spek'] != "-":
                        info_barang += f" - _{item['spek']}_" # Tambahin spek pake tulisan miring
                    
                    laporan_dict[lok].append(info_barang)

                teks_laporan = f"📝 *LAPORAN PENGAMBILAN BARANG*\n"
                teks_laporan += f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                teks_laporan += "-------------------------------------------\n"
                
                for lokasi, daftar_barang in laporan_dict.items():
                    teks_laporan += f"\n📍 *Lokasi: {lokasi}*\n"
                    for b in daftar_barang: 
                        teks_laporan += f"  - {b}\n"
                
                st.info(teks_laporan)
                st.write("Salin laporan di bawah ini:")
                st.code(teks_laporan, language=None)
                
                # --- TOMBOL KOSONGKAN YANG BENER ---
                if st.button("🗑️ Kosongkan Keranjang"):
                    st.session_state['cart'] = {}
                    st.session_state['reset_cnt'] += 1 # Ganti identitas semua widget qty
                    st.rerun()
        else:
            st.info("Belum ada data aset.")
    with tab_add:
        if st.session_state['role'] == "admin":
            st.markdown("### ➕ Tambah Aset Baru")
            
            # 1. Standarisasi Nama Barang
            list_barang_ada = sorted(df_inv['Nama Barang'].unique().tolist()) if not df_inv.empty else []
            opsi_nama = ["-- Tambah Nama Baru --"] + list_barang_ada
            pilih_nama_inv = st.selectbox("Pilih Nama Barang (Standar):", opsi_nama)
            
            if pilih_nama_inv == "-- Tambah Nama Baru --":
                nb = st.text_input("Ketik Nama Barang Baru (Contoh: Lampu LED 30W)")
            else:
                nb = pilih_nama_inv
            
            # 2. Lokasi dari Data Warga
            list_warga = sorted(df_warga['Nama'].tolist()) if not df_warga.empty else []
            lok_warga = st.selectbox("Lokasi Awal (Nama Warga):", ["Pilih Warga/Lokasi"] + list_warga)
            
            with st.form("f_inv_add_new", clear_on_submit=True):
                c1, c2 = st.columns(2)
                sp = c1.text_input("Spesifikasi (Contoh: Philips)")
                jml = c2.number_input("Total Unit", min_value=1, value=1)
                img_link = st.text_input("Link Foto Barang (G-Drive)") # Input Link Foto
                
                if st.form_submit_button("Simpan Barang"):
                    if nb and lok_warga != "Pilih Warga/Lokasi":
                        # Tambahkan kolom Link Foto di baris ke-9 Google Sheets
                        sh.worksheet("Inventaris").append_row([nb, sp, int(jml), lok_warga, "Baik", "Tersedia", 0, "-", img_link])
                        st.success("Barang berhasil ditambah!"); st.cache_data.clear(); time.sleep(1); st.rerun()
                    else: st.error("Nama Barang & Lokasi wajib diisi!")
        else: 
            st.warning("Menu ini hanya untuk Admin.")

    with tab_edit:
        if not df_inv.empty:
            st.markdown("### 🔄 Update Status & Peminjaman")

            # 1. Bikin Label (Nama + Lokasi + Kondisi)
            df_inv['label_edit'] = (
                df_inv['Nama Barang'] + " [" + 
                df_inv['Lokasi'].astype(str) + "] - (" + 
                df_inv['Kondisi'] + ")"
            )

            # 2. URUTKAN SESUAI ABJAD (A-Z)
            # Kita urutkan berdasarkan label_edit biar rapi pas dibaca di dropdown
            pilihan_urut = sorted(df_inv['label_edit'].tolist())

            # 3. Langsung Selectbox (Tanpa kolom search teks)
            pilih_barang = st.selectbox("Pilih Barang (Sudah Urut Abjad):", pilihan_urut)
            
            # Filter data asli untuk dapet baris 'curr'
            if pilih_barang:
                df_filtered = df_inv[df_inv['label_edit'] == pilih_barang]
                if not df_filtered.empty:
                    curr = df_filtered.iloc[0]

                    with st.form("f_inv_update"):
                        c1, c2 = st.columns(2)
                        n_dipinjam = c1.number_input("Jumlah Dipinjam", 0, int(curr['Jumlah']), int(curr['Dipinjam']))
                        
                        list_k = ["Baik", "Rusak Ringan", "Rusak Parah"]
                        idx_k = list_k.index(curr['Kondisi']) if curr['Kondisi'] in list_k else 0
                        n_kondisi = c2.selectbox("Kondisi Barang", list_k, index=idx_k)
                        
                        # Ambil list warga buat lokasi
                        list_warga = sorted(df_warga['Nama'].tolist()) if not df_warga.empty else []
                        list_lokasi = ["Pilih Lokasi"] + list_warga
                        
                        try:
                            idx_l = list_lokasi.index(curr['Lokasi'])
                        except:
                            idx_l = 0
                        
                        n_lokasi = st.selectbox("Update Lokasi (Pindah ke Warga)", options=list_lokasi, index=idx_l)
                        n_peminjam = st.text_input("Nama Peminjam / Keperluan", value=curr['Keterangan'])
                        
                        if st.form_submit_button("💾 Simpan Perubahan"):
                            if n_lokasi != "Pilih Lokasi":
                                idx = get_row_index(ws_inv, curr['Nama Barang'], curr['Lokasi'])
                                if idx:
                                    status_txt = "Dipinjam" if n_dipinjam > 0 else "Tersedia"
                                    ws_inv.update_cell(idx, 4, n_lokasi)
                                    ws_inv.update_cell(idx, 5, n_kondisi)
                                    ws_inv.update_cell(idx, 6, status_txt)
                                    ws_inv.update_cell(idx, 7, int(n_dipinjam))
                                    ws_inv.update_cell(idx, 8, n_peminjam)
                                    
                                    st.success(f"Data {curr['Nama Barang']} berhasil diupdate!")
                                    st.cache_data.clear(); time.sleep(1); st.rerun()
                            else:
                                st.error("Pilih lokasi dulu bray!")
            # 2. Fitur Pecah Stok (Terbuka untuk Umum)
            with st.expander("🛠️ Fitur Pecah Stok (Jika sebagian unit rusak/pindah)"):
                if int(curr['Jumlah']) > 1:
                    with st.form("f_split_stok"):
                        st.write(f"Mengolah sebagian dari total {curr['Jumlah']} unit '{curr['Nama Barang']}'")
                        c_jml, c_aksi = st.columns(2)
                        j_potong = c_jml.number_input("Jumlah unit", 1, int(curr['Jumlah'])-1)
                        opsi = c_aksi.radio("Tindakan:", ["Pindah Lokasi", "Lapor Rusak"])
                        
                        # --- PERBAIKAN 1: AMBIL DARI DATA WARGA ---
                        list_warga = sorted(df_warga['Nama'].tolist()) if not df_warga.empty else []
                        if opsi == "Pindah Lokasi":
                            tujuan_baru = st.selectbox("Pindah ke Lokasi (Warga):", list_warga)
                        else:
                            tujuan_baru = st.text_input("Info Kerusakan", placeholder="Misal: Pecah/Mati total")

                        if st.form_submit_button("Konfirmasi Pecah"):
                            idx_asal = get_row_index(ws_inv, curr['Nama Barang'], curr['Lokasi'])
                            
                            # 1. Update stok di baris asal (dikurangi)
                            ws_inv.update_cell(idx_asal, 3, int(curr['Jumlah'] - j_potong))
                            
                            # --- PERBAIKAN 2: BAWA LINK FOTO KE BARIS BARU ---
                            n_lok = tujuan_baru if opsi == "Pindah Lokasi" else curr['Lokasi']
                            n_kon = curr['Kondisi'] if opsi == "Pindah Lokasi" else "Rusak Ringan"
                            # Pastikan curr['Link Foto'] ikut dimasukkan ke kolom ke-9
                            link_foto_lama = curr['Link Foto'] if 'Link Foto' in curr else "-"
                            
                            ws_inv.append_row([
                                curr['Nama Barang'], 
                                curr['Spesifikasi'], 
                                int(j_potong), 
                                n_lok, 
                                n_kon, 
                                "Tersedia", 
                                0, 
                                tujuan_baru, 
                                link_foto_lama # <--- Ini kuncinya biar gambar gak ilang bray!
                            ])
                            
                            st.success("Berhasil dipecah!"); st.cache_data.clear(); time.sleep(1); st.rerun()
                else:
                    st.caption("Unit hanya ada 1, gunakan form utama di atas.")
            # --- INI BAGIAN HAPUS ASET (CUMA ADMIN) ---
        with st.expander("🗑️ Zona Bahaya (Hapus Aset)"):
            if st.session_state.get('role') == "admin": # Cek apakah dia admin
                with st.form("f_delete_aset"):
                    alasan = st.text_input("Alasan Penghapusan")
                    if st.form_submit_button("Hapus Permanen"):
                        idx_del = get_row_index(ws_inv, curr['Nama Barang'], curr['Lokasi'])
                        if idx_del:
                            ws_inv.delete_rows(idx_del) # Hapus baris di Google Sheets
                            st.success("Aset berhasil dihapus!"); st.cache_data.clear(); time.sleep(1); st.rerun()
            else:
                # Pesan kalau bukan admin
                st.warning("Hanya Admin yang bisa menghapus aset dari daftar permanen.")
# --- 9. LOG KAS BULANAN & LAINNYA ---
elif menu == "📥 Kas Bulanan" and st.session_state['role'] == "admin":
    st.subheader("📥 Input Keuangan")
    tipe_transaksi = st.radio("Pilih Tipe Input:", ["Iuran Rutin", "Hibah/Dana Tambahan"], horizontal=True)

    if tipe_transaksi == "Iuran Rutin":
        warga_options = [f"{n}" for n in list_warga_input] if not df_warga.empty else []
        selected_display = st.selectbox("Pilih Nama Warga", warga_options)
        w_pilih = selected_display.split(" (")[0]
        mode = st.radio("Mode Alokasi:", ["Paket Lengkap (50rb)", "Hanya Kas (15rb)", "Hanya Hadiah (35rb)", "Custom"], horizontal=True)
        
        with st.form("f_kas_rutin", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            n = c1.number_input("Nominal (Rp)", value=50000 if mode != "Custom" else 0, step=5000)
            t_input = c2.selectbox("Tahun Mulai", range(2022, 2031), index=4)
            b_input = c3.selectbox("Bulan Mulai", bln_list)
            
            if st.form_submit_button("🚀 Proses Iuran"):
                uang_sisa, bulan_idx, tahun_jalan = n, bln_list.index(b_input), t_input
                input_log = []
                
                # Loop untuk alokasi bulanan
                while uang_sisa > 0 and tahun_jalan <= (datetime.now().year + 1):
                    curr_month = bln_list[bulan_idx]
                    df_curr = df_masuk[(df_masuk['Nama'] == w_pilih) & (df_masuk['Tahun'] == tahun_jalan) & (df_masuk['Bulan'] == curr_month)]
                    kas_terbayar = df_curr['Kas'].sum()
                    hadiah_terbayar = df_curr['Hadiah'].sum()
                    
                    # Target nominal
                    target_k, target_h = (15000, 35000) if mode != "Hanya Kas (15rb)" and mode != "Hanya Hadiah (35rb)" else (15000 if mode == "Hanya Kas (15rb)" else 0, 35000 if mode == "Hanya Hadiah (35rb)" else 0)
                    j_kas, j_hadiah = max(0, target_k - kas_terbayar), max(0, target_h - hadiah_terbayar)
                    
                    if j_kas == 0 and j_hadiah == 0:
                        bulan_idx += 1
                        if bulan_idx >= 12: bulan_idx = 0; tahun_jalan += 1
                        continue
                    
                    pakai_kas = min(uang_sisa, j_kas); uang_sisa -= pakai_kas
                    pakai_hadiah = min(uang_sisa, j_hadiah); uang_sisa -= pakai_hadiah
                    
                    if (pakai_kas + pakai_hadiah) > 0:
                        sh.worksheet("Pemasukan").append_row([datetime.now().strftime("%d/%m/%Y"), w_pilih, tahun_jalan, curr_month, int(pakai_kas + pakai_hadiah), int(pakai_kas), int(pakai_hadiah), "LUNAS", "Iuran"])
                        input_log.append(f"{curr_month} {tahun_jalan}")
                    
                    bulan_idx += 1
                    if bulan_idx >= 12: bulan_idx = 0; tahun_jalan += 1
                
                st.success(f"✅ Input sukses: {', '.join(input_log)}")
                st.cache_data.clear(); time.sleep(1); st.rerun()

    else: # Mode Hibah (Langsung ke Saldo)
        with st.form("f_hibah", clear_on_submit=True):
            nominal = st.number_input("Nominal Hibah (Rp)", step=5000)
            keterangan = st.text_input("Keterangan (Contoh: Hibah dari Hamba Allah)")
            if st.form_submit_button("💰 Simpan Hibah ke Saldo"):
                # Input dengan nama 'HIBAH' agar tidak dianggap iuran bulanan
                sh.worksheet("Pemasukan").append_row([datetime.now().strftime("%d/%m/%Y"), "HIBAH", datetime.now().year, "-", int(nominal), int(nominal), 0, "HIBAH", keterangan])
                st.success("Hibah berhasil ditambah ke saldo kas!")
                st.cache_data.clear(); time.sleep(1); st.rerun()
elif menu == "📤 Pengeluaran" and st.session_state['role'] in ["admin", "event_manager"]:
    
    # Logika Penentuan Kategori
    if st.session_state['role'] == "admin":
        kat_pilih = st.radio("Sumber Dana:", ["Kas", "Hadiah", "Event"], horizontal=True)
    else:
        st.write("Mode Input: **Pengeluaran Event**")
        kat_pilih = "Event"

    with st.form("f_out", clear_on_submit=True):
        # Dropdown event hanya muncul jika kategori adalah "Event"
        if kat_pilih == "Event":
            options = ["N/A"] + (df_event['Nama Event'].unique().tolist() if not df_event.empty else [])
            ev_ref = st.selectbox("Event:", options)
        else:
            ev_ref = "N/A"
            
        nom, ket = st.number_input("Nominal", min_value=0), st.text_input("Keterangan")
        
        if st.form_submit_button("Simpan"):
            # Validasi nominal biar gak 0
            if nom > 0:
                sh.worksheet("Pengeluaran").append_row([
                    datetime.now().strftime("%d/%m/%Y"), 
                    kat_pilih, 
                    int(nom), 
                    f"[{ev_ref}] {ket}" if kat_pilih == "Event" else ket
                ])
                st.success("Tercatat!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
            else:
                st.error("Nominal harus lebih dari 0!")

elif menu == "👥 Kelola Warga" and st.session_state['role'] == "admin":
    st.markdown("### 👥 Manajemen Warga & Hak Akses")
    
    # 1. Tampilkan Data Warga (termasuk kolom Status)
    st.dataframe(df_warga[['Nama', 'Role', 'Status']], hide_index=True, use_container_width=True)
    
    tab_update, tab_tambah = st.tabs(["🔄 Update / Hapus Warga", "➕ Tambah Warga Baru"])
    
    with tab_update:
        if not df_warga.empty:
            pilih_nama = st.selectbox("Pilih Warga yang mau di-edit:", df_warga['Nama'].tolist())
            curr_warga = df_warga[df_warga['Nama'] == pilih_nama].iloc[0]
            
            with st.form("f_edit_warga"):
                nama_baru = st.text_input("Nama Warga", value=curr_warga['Nama'])
                role_baru = st.selectbox("Role", ["Main Warga", "Warga Support"], 
                                       index=0 if curr_warga['Role'] == "Main Warga" else 1)
                
                # Opsi Status (Pahmi bakal muncul di sini kalau kamu ganti ke 'Alumni')
                opsi_status = ["Aktif", "Non-Warga", "Alumni"]
                status_idx = opsi_status.index(curr_warga['Status']) if curr_warga['Status'] in opsi_status else 0
                status_baru = st.selectbox("Status", opsi_status, index=status_idx)
                
                col1, col2 = st.columns(2)
                if col1.form_submit_button("💾 Simpan Perubahan"):
                    ws_w = sh.worksheet("Warga")
                    # Cari baris (Asumsi Nama kolom 1, Role kolom 2, Status kolom 3)
                    idx_w = get_row_index(ws_w, pilih_nama, role=curr_warga['Role'])
                    
                    if idx_w:
                        ws_w.update_cell(idx_w, 1, nama_baru)
                        ws_w.update_cell(idx_w, 2, role_baru)
                        ws_w.update_cell(idx_w, 3, status_baru)
                        st.success(f"Berhasil update {nama_baru}!")
                        st.cache_data.clear(); time.sleep(1); st.rerun()
                
                if col2.form_submit_button("🗑️ Hapus Warga"):
                    ws_w = sh.worksheet("Warga")
                    idx_w = get_row_index(ws_w, pilih_nama, role=curr_warga['Role'])
                    if idx_w:
                        ws_w.delete_rows(idx_w)
                        st.warning(f"Warga {pilih_nama} dihapus.")
                        st.cache_data.clear(); time.sleep(1); st.rerun()

    with tab_tambah:
        with st.form("t_w_baru"):
            nw = st.text_input("Nama Warga Baru")
            nr = st.selectbox("Role", ["Main Warga", "Warga Support"])
            ns = st.selectbox("Status", ["Aktif", "Non-Warga", "Alumni"])
            if st.form_submit_button("Tambah Warga"):
                if nw:
                    sh.worksheet("Warga").append_row([nw, nr, ns])
                    st.success("Warga berhasil ditambahkan!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()

elif menu == "🎭 Event & Iuran":
    # Pastikan kedua role ini bisa akses form input
    if st.session_state['role'] in ["admin", "event_manager"]:
        st.subheader("📝 Input Data Event")
    with st.form("f_ev", clear_on_submit=True):
        ev_p = st.selectbox("Event", ["-- Baru --"] + (df_event['Nama Event'].unique().tolist() if not df_event.empty else []))
        ev_n = st.text_input("Nama Event Baru") if ev_p == "-- Baru --" else ev_p
        w_e, j_e = st.selectbox("Warga", sorted(df_warga['Nama'].tolist())), st.number_input("Jumlah", step=5000)
        if st.form_submit_button("Simpan"):
            # Validasi tambahan
            event_name = ev_n.strip() # Hilangkan spasi di depan/belakang
            if not event_name:
                st.error("Nama Event tidak boleh kosong!")
            elif j_e <= 0:
                st.error("Jumlah harus lebih dari 0!")
            else:
                # Baru eksekusi kalau valid
                sh.worksheet("Event").append_row([datetime.now().strftime("%d/%m/%Y"), w_e, event_name, int(j_e)])
                st.success("Data berhasil disimpan!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
elif menu == "💸 Dana Talangan" and st.session_state['role'] == "admin":
    st.subheader("💸 Manajemen Talangan & Piutang")
    t1, t2 = st.tabs(["📝 Input Transaksi", "📋 Daftar Piutang"])
    
    with t1:
        with st.form("form_talangan", clear_on_submit=True):
            # Di file lo variabelnya df_warga
            nama_t = st.selectbox("Pilih Nama", sorted(df_warga['Nama'].tolist()))
            aksi_t = st.radio("Aksi", ["PINJAM", "BAYAR (Cicil)"], horizontal=True)
            nominal_t = st.number_input("Nominal (Rp)", step=5000)
            ket_t = st.text_input("Keterangan")
            
            if st.form_submit_button("Simpan Data"):
                tipe_fix = "PINJAM" if aksi_t == "PINJAM" else "BAYAR"
                sh.worksheet("Talangan").append_row([
                    datetime.now().strftime("%d/%m/%Y"), 
                    nama_t, tipe_fix, int(nominal_t), ket_t
                ])
                st.success("Data Berhasil Disimpan!")
                st.cache_data.clear(); time.sleep(1); st.rerun()

    with t2:
        df_p = get_sisa_piutang()
        if not df_p.empty:
            st.table(df_p)
            st.warning(f"Total Piutang: **Rp {df_p['Sisa Utang'].sum():,}**")
        else:
            st.info("Tidak ada piutang aktif.")
elif menu == "📜 Log":
    st.dataframe(df_masuk.tail(20), hide_index=True, use_container_width=True)
