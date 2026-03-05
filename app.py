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

# --- 4. SIDEBAR ---
with st.sidebar:
    # Bikin kolom buat centering logo (karena st.image defaultnya kiri)
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=100)
    # Tambahkan Motto di bawah logo
    st.markdown("""
        <div style='text-align: center; margin-top: -30px; margin-bottom: 20px;'>
            <i style='font-size: 14px; color: #666;'>
                "We come to learn & bring science back"
            </i>
        </div>
    """, unsafe_allow_html=True)
    
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

    if st.session_state['role'] == "admin":
        list_menu = ["📊 Laporan", "📚 Pustaka", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📦 Inventaris", "📜 Log"]
    else:
        list_menu = ["📊 Laporan", "📚 Pustaka", "📦 Inventaris", "📜 Log"]
    
    menu = st.radio("NAVIGASI", list_menu)

# --- 5. LOGIKA DISPLAY ---
st.title(f"{menu}")

in_k, in_h, in_e = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum(), df_event['Jumlah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
out_e = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum()

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
            pesan_wa = (f"📢 *LAPORAN KAS AR-ROYHAAN 3*\n📅 _Update: {datetime.now().strftime('%d/%m/%Y')}_\n\n*Saldo Kas:* Rp {sk:,}\n*Saldo Hadiah:* Rp {shd:,}\n━━━━━━━━━━━━━━━━━━\n*TOTAL DANA: Rp {sk+shd:,}*\n\nSyukron jazakumullah khair. 🙏")
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
                        p_url = row['Link'].replace('/view', '/preview') if '/view' in row['Link'] else row['Link']
                        st.markdown(f'<iframe src="{p_url}" width="100%" height="150" style="border:none; border-radius:10px;"></iframe>', unsafe_allow_html=True)
                        st.link_button("🚀 Putar di G-Drive", row['Link'])
                    elif row['Tipe'] == "PDF":
                        st.markdown(f'<iframe src="{gdrive_fix(row["Link"])}" width="100%" height="500px"></iframe>', unsafe_allow_html=True)
                    elif row['Tipe'] == "Gambar":
                        file_id = ""
                        url_g = row['Link']
                        if '/d/' in url_g: file_id = url_g.split('/d/')[1].split('/')[0]
                        elif 'id=' in url_g: file_id = url_g.split('id=')[1].split('&')[0]
                        if file_id:
                            st.image(f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000", use_container_width=True)
                        st.link_button("📂 Buka Gambar Asli", row['Link'])
            st.divider()

elif menu == "📊 Laporan":
    t1, t2, t3 = st.tabs(["💰 Rekap Bulanan", "🎭 Detail Event", "📤 Riwayat Pengeluaran"])
    with t1:
        thn = st.selectbox("Pilih Tahun Laporan", range(2022, 2031), index=4)
        
        # 1. Pastikan data iuran digabung dengan data warga buat tau Role-nya
        df_y = df_masuk[df_masuk['Tahun'] == thn].copy()
        
        if not df_y.empty and not df_warga.empty:
            # Gabungkan Role ke data iuran
            df_y = df_y.merge(df_warga[['Nama', 'Role']], on='Nama', how='left')
            df_y['Bulan'] = pd.Categorical(df_y['Bulan'], categories=bln_list, ordered=True)

            # 2. INI FUNGSI STYLING-NYA (Taruh di sini)
            def warna_iuran(df_pivot, target_nominal):
                def terapkan_style(row):
                    nama_idx = row.name
                    # Cek role warga dari data utama
                    role = df_warga[df_warga['Nama'] == nama_idx]['Role'].values[0] if nama_idx in df_warga['Nama'].values else "Main Warga"
                    
                    styles = []
                    for nilai in row:
                        # Syarat Merah: Role Main DAN Bayar > 0 DAN Bayar < Target
                        if role == "Main Warga" and 0 < nilai < target_nominal:
                            styles.append('color: red; font-weight: bold')
                        else:
                            styles.append('color: black')
                    return styles
                return df_pivot.style.apply(terapkan_style, axis=1)

            # 3. TAMPILKAN TABEL KAS
            st.write("#### 🟢 Kas (Target Main: 15rb)")
            p_kas = df_y.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum', observed=False).fillna(0).astype(int)
            # Panggil fungsi styling di sini
            st.dataframe(warna_iuran(p_kas, 15000), use_container_width=True)
            
            # 4. TAMPILKAN TABEL HADIAH
            st.write("#### 🟡 Hadiah (Target Main: 35rb)")
            p_had = df_y.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum', observed=False).fillna(0).astype(int)
            # Panggil fungsi styling di sini
            st.dataframe(warna_iuran(p_had, 35000), use_container_width=True)
            
            st.info("💡 **Merah Bold:** Hanya berlaku untuk 'Main Warga' yang cicilannya belum mencapai target kewajiban.")
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

elif menu == "📦 Inventaris":
    tab_view, tab_add, tab_edit = st.tabs(["📋 Daftar Aset", "➕ Tambah Baru", "🔄 Update Status"])
    with tab_view:
        if not df_inv.empty:
            # Pastikan kolom angka aman
            df_inv['Jumlah'] = pd.to_numeric(df_inv['Jumlah'], errors='coerce').fillna(0).astype(int)
            df_inv['Dipinjam'] = pd.to_numeric(df_inv.get('Dipinjam', 0), errors='coerce').fillna(0).astype(int)
            df_inv['Tersedia'] = df_inv['Jumlah'] - df_inv['Dipinjam']
            
            # --- KOLOM SUDAH LENGKAP DI SINI ---
            cols_show = ['Nama Barang', 'Spesifikasi', 'Jumlah', 'Dipinjam', 'Tersedia', 'Lokasi', 'Kondisi', 'Keterangan']
            st.dataframe(df_inv[cols_show], hide_index=True, use_container_width=True)
            
            # --- FIX SYNTAX WA (TANPA BACKSLASH DI F-STRING) ---
            summary = [f"- {r['Nama Barang']}: {r['Dipinjam']} unit ({r['Keterangan']})" for _, r in df_inv.iterrows() if r['Dipinjam'] > 0]
            txt_pinjam = "\n".join(summary) if summary else "Semua Aman di Tempat."
            p_wa = f"📦 *UPDATE ASET AR-ROYHAAN 3*\n📅 _{datetime.now().strftime('%d/%m/%Y')}_\n\n*STATUS PINJAM:*\n{txt_pinjam}"
            p_wa_enc = p_wa.replace(' ', '%20').replace('\n', '%0A')
            st.link_button("📲 Share ke WA", f"https://wa.me/?text={p_wa_enc}")

    with tab_add:
        if st.session_state['role'] == "admin":
            with st.form("f_inv_add", clear_on_submit=True):
                nb, sp, jml, lok = st.text_input("Nama Barang"), st.text_input("Spesifikasi"), st.number_input("Total Stok", min_value=1), st.text_input("Lokasi")
                if st.form_submit_button("Simpan"):
                    sh.worksheet("Inventaris").append_row([nb, sp, int(jml), lok, "Baik", "Tersedia", 0, "-"])
                    st.success("Tersimpan!"); st.cache_data.clear(); time.sleep(1); st.rerun()
        else: st.warning("Khusus Admin.")

    with tab_edit:
        if not df_inv.empty:
            with st.form("f_inv_edit"):
                b_edit = st.selectbox("Pilih Barang", df_inv['Nama Barang'].tolist())
                curr = df_inv[df_inv['Nama Barang'] == b_edit].iloc[0]
                
                c1, c2 = st.columns(2)
                n_dipinjam = c1.number_input("Jumlah Dipinjam", min_value=0, max_value=int(curr['Jumlah']), value=int(curr.get('Dipinjam', 0)))
                n_k = c2.selectbox("Kondisi", ["Baik", "Rusak Ringan", "Rusak Parah"], index=["Baik", "Rusak Ringan", "Rusak Parah"].index(curr['Kondisi']))
                
                # --- INPUT LOKASI & PEMINJAM SUDAH KEMBALI ---
                n_lok = st.text_input("Update Lokasi (Gudang/Teras/dll)", value=curr.get('Lokasi', '-'))
                n_ket = st.text_input("Peminjam / Keperluan", value=curr.get('Keterangan', '-'))
                
                if st.form_submit_button("Update Data"):
                    try:
                        r = sh.worksheet("Inventaris").find(b_edit).row
                        # Update Kolom 4 (Lokasi), 5 (Kondisi), 7 (Jml Dipinjam), 8 (Keterangan)
                        sh.worksheet("Inventaris").update_cell(r, 4, n_lok) # Balikin update lokasi
                        sh.worksheet("Inventaris").update_cell(r, 5, n_k)
                        sh.worksheet("Inventaris").update_cell(r, 7, int(n_dipinjam))
                        
                        f_k = n_ket if n_dipinjam > 0 else "-"
                        sh.worksheet("Inventaris").update_cell(r, 8, f_k)
                        
                        # Update status teks di kolom 6 (Tersedia/Dipinjam)
                        st_teks = "Dipinjam" if n_dipinjam > 0 else "Tersedia"
                        sh.worksheet("Inventaris").update_cell(r, 6, st_teks)
                        
                        st.success(f"✅ Data {b_edit} Berhasil Diperbarui!"); st.cache_data.clear(); time.sleep(1); st.rerun()
                    except: 
                        st.error("Gagal update. Cek koneksi atau nama barang.")

# --- MENU INPUT KAS ---
elif menu == "📥 Kas Bulanan" and st.session_state['role'] == "admin":
    st.subheader("📥 Input Pembayaran Iuran")
    
    # 1. Daftar Warga
    warga_options = []
    if not df_warga.empty:
        for _, row in df_warga.iterrows():
            warga_options.append(f"{row['Nama']} ({row['Role']})")
    warga_options.sort()
    
    selected_display = st.selectbox("Pilih Nama Warga", warga_options)
    w_pilih = selected_display.split(" (")[0]
    
    mode = st.radio("Pilih Mode Alokasi Dana:", 
                    ["Paket Lengkap (50rb)", "Hanya Kas (15rb)", "Hanya Hadiah (35rb)", "Custom Nominal"], 
                    horizontal=True)
    
    n_val = 50000 if "Paket Lengkap" in mode else 15000 if "Hanya Kas" in mode else 35000 if "Hanya Hadiah" in mode else 0
    
    with st.form("f_kas", clear_on_submit=True):
        c_nom, c_thn, c_bln = st.columns([2, 1, 1])
        n = c_nom.number_input("Nominal Total yang Diterima (Rp)", value=n_val, step=5000)
        t_input = c_thn.selectbox("Tahun Mulai", range(2022, 2031), index=4) # Default 2026
        b_input = c_bln.selectbox("Bulan Mulai", bln_list)
        
        if st.form_submit_button("🚀 Proses & Simpan Pembayaran"):
            uang_sisa = n
            bulan_idx = bln_list.index(b_input)
            tahun_jalan = t_input
            input_log = []
            
            # Ambil Role
            row_warga = df_warga[df_warga['Nama'] == w_pilih]
            role_warga = row_warga['Role'].values[0] if not row_warga.empty else "Main Warga"

            # LOOPING SAKTI: Selama uang masih ada, hajar terus bulan & tahun depan
            max_loop = 60 # Safety: Maksimal ngejar sampai 5 tahun ke depan
            loops = 0

            while uang_sisa > 0 and loops < max_loop:
                loops += 1
                curr_month = bln_list[bulan_idx]
                
                # Cek data yang sudah ada di bulan & tahun ini
                df_curr = df_masuk[(df_masuk['Nama'] == w_pilih) & 
                                  (df_masuk['Tahun'] == tahun_jalan) & 
                                  (df_masuk['Bulan'] == curr_month)]
                
                kas_terbayar = df_curr['Kas'].sum()
                hadiah_terbayar = df_curr['Hadiah'].sum()

                # Hitung Jatah Sisa
                if mode == "Hanya Kas (15rb)":
                    j_kas, j_hadiah = max(0, 15000 - kas_terbayar), 0
                elif mode == "Hanya Hadiah (35rb)":
                    j_kas, j_hadiah = 0, max(0, 35000 - hadiah_terbayar)
                else: 
                    j_kas, j_hadiah = max(0, 15000 - kas_terbayar), max(0, 35000 - hadiah_terbayar)
                
                # Jika bulan ini sudah lunas sesuai mode, lanjut bulan depan
                if j_kas <= 0 and j_hadiah <= 0:
                    bulan_idx += 1
                    if bulan_idx >= 12:
                        bulan_idx = 0
                        tahun_jalan += 1
                    continue

                # Alokasi
                pakai_kas = min(uang_sisa, j_kas)
                uang_sisa -= pakai_kas
                pakai_hadiah = min(uang_sisa, j_hadiah)
                uang_sisa -= pakai_hadiah
                
                total_baris = pakai_kas + pakai_hadiah
                
                if total_baris > 0:
                    tipe_db = mode.split(" (")[0]
                    if role_warga == "Warga Support":
                        status_db = "PARTISIPASI"
                    else:
                        status_db = "LUNAS" if (kas_terbayar + hadiah_terbayar + total_baris) >= 50000 else "BELUM LUNAS"
                    
                    try:
                        sh.worksheet("Pemasukan").append_row([
                            datetime.now().strftime("%d/%m/%Y"), w_pilih, tahun_jalan, curr_month, 
                            int(total_baris), int(pakai_kas), int(pakai_hadiah), status_db, tipe_db
                        ])
                        input_log.append(f"{curr_month} {tahun_jalan}")
                    except Exception as e:
                        st.error(f"Gagal simpan: {e}")
                        break

                # Pindah bulan setelah alokasi
                bulan_idx += 1
                if bulan_idx >= 12:
                    bulan_idx = 0
                    tahun_jalan += 1

            if input_log:
                st.success(f"✅ Berhasil diinput ke: {', '.join(input_log)}")
                if uang_sisa > 0:
                    st.warning(f"⚠️ Sisa Rp {uang_sisa:,} tidak terinput (Sudah lunas s/d 5 tahun ke depan)")
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()
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
