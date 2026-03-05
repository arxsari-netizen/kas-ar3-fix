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
# --- HELPER FUNCTIONS ---
def get_row_index(worksheet, nama_barang, lokasi):
    # Mengambil semua nilai mentah (list of lists)
    data = worksheet.get_all_values()
    # Asumsi: baris 1 adalah header, data mulai baris 2 (index 1)
    for i, row in enumerate(data[1:], start=2):
        # row[0] = Nama Barang, row[3] = Lokasi (menurut struktur sheet kamu)
        # .strip() untuk membersihkan spasi di awal/akhir
        if row[0].strip() == str(nama_barang).strip() and row[3].strip() == str(lokasi).strip():
            return i
    return None
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
    tab_view, tab_add, tab_edit = st.tabs(["📋 Daftar Aset", "➕ Tambah Baru", "🔄 Update Status"])
    ws_inv = sh.worksheet("Inventaris")

    with tab_view:
        if not df_inv.empty:
            # Kalkulasi stok tersedia di memori (biar cepet)
            df_inv['Tersedia'] = df_inv['Jumlah'] - df_inv['Dipinjam']
            st.dataframe(
                df_inv[['Nama Barang', 'Spesifikasi', 'Jumlah', 'Dipinjam', 'Tersedia', 'Lokasi', 'Kondisi', 'Keterangan']], 
                hide_index=True, 
                use_container_width=True
            )
            
            # Olah pesan WA di luar f-string biar gak error backslash
            summary = [f"- {r['Nama Barang']} ({r['Dipinjam']} unit)" for _, r in df_inv.iterrows() if r['Dipinjam'] > 0]
            txt_wa = "📦 *STATUS PINJAM ASET:*\n" + ("\n".join(summary) if summary else "Semua aman di tempat.")
            txt_encoded = txt_wa.replace(' ', '%20').replace('\n', '%0A')
            st.link_button("📲 Share Status ke WA", f"https://wa.me/?text={txt_encoded}")

    with tab_add:
        if st.session_state['role'] == "admin":
            with st.form("f_inv_add", clear_on_submit=True):
                st.markdown("### ➕ Tambah Aset Baru")
                c1, c2 = st.columns(2)
                nb = c1.text_input("Nama Barang (Contoh: Lampu 30W)")
                sp = c2.text_input("Spesifikasi (Contoh: Philips LED)")
                jml = c1.number_input("Total Unit", min_value=1, value=1)
                lok = c2.text_input("Lokasi Awal")
                if st.form_submit_button("Simpan Barang"):
                    if nb and lok:
                        ws_inv.append_row([nb, sp, int(jml), lok, "Baik", "Tersedia", 0, "-"])
                        st.success("Barang berhasil ditambah!"); st.cache_data.clear(); time.sleep(1); st.rerun()
                    else: st.error("Nama & Lokasi wajib diisi!")
        else: st.warning("Menu ini hanya untuk Admin.")

    with tab_edit:
        # Pindahkan pengecekan role ke dalam fitur spesifik
        if not df_inv.empty:
            # 1. Bikin Label yang Informatif
            df_inv['label_edit'] = (
                df_inv['Nama Barang'] + " [" + 
                df_inv['Lokasi'].astype(str) + "] - (" + 
                df_inv['Kondisi'] + ")"
            )

            st.markdown("### 🔄 Update Status & Peminjaman")
            st.info("💡 Semua warga dapat memperbarui status peminjaman atau lokasi barang.")
            
            # Selectbox di luar form biar reaktif
            # --- UBAH BAGIAN INI ---
            # Kita paksa ambil list terbaru dari df_inv yang fresh
            pilihan = df_inv['label_edit'].tolist()
            pilih_barang = st.selectbox("Pilih Barang:", pilihan)
            
            # Filter ulang berdasarkan pilihan agar 'curr' tidak ambil index yang salah
            df_filtered = df_inv[df_inv['label_edit'] == pilih_barang]
            if not df_filtered.empty:
                curr = df_filtered.iloc[0]

            with st.form("f_inv_update"):
                c1, c2 = st.columns(2)
                
                # Input otomatis terisi sesuai data 'curr'
                n_dipinjam = c1.number_input("Jumlah Dipinjam", 0, int(curr['Jumlah']), int(curr['Dipinjam']))
                
                list_k = ["Baik", "Rusak Ringan", "Rusak Parah"]
                idx_k = list_k.index(curr['Kondisi']) if curr['Kondisi'] in list_k else 0
                n_kondisi = c2.selectbox("Kondisi Barang", list_k, index=idx_k)
                
                n_lokasi = st.text_input("Update Lokasi", value=curr['Lokasi'])
                n_peminjam = st.text_input("Nama Peminjam / Keperluan", value=curr['Keterangan'])
                
                if st.form_submit_button("💾 Simpan Perubahan"):
    idx = get_row_index(ws_inv, curr['Nama Barang'], curr['Lokasi'])
    if idx:
        status_txt = "Dipinjam" if n_dipinjam > 0 else "Tersedia"
        
        # Update satu per satu per kolom (D=4, E=5, F=6, G=7, H=8)
        ws_inv.update_cell(idx, 4, n_lokasi)
        ws_inv.update_cell(idx, 5, n_kondisi)
        ws_inv.update_cell(idx, 6, status_txt)
        ws_inv.update_cell(idx, 7, int(n_dipinjam))
        ws_inv.update_cell(idx, 8, n_peminjam)
        
        st.success("Data berhasil diperbarui ke Google Sheets!")
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()
    else:
        st.error(f"Gagal menemukan baris untuk '{curr['Nama Barang']}'. Cek spasi di Google Sheets!")

            st.divider()

            # 2. Fitur Pecah Stok (Terbuka untuk Umum)
            with st.expander("🛠️ Fitur Pecah Stok (Jika sebagian unit rusak/pindah)"):
                if int(curr['Jumlah']) > 1:
                    with st.form("f_split_stok"):
                        st.write(f"Mengolah sebagian dari total {curr['Jumlah']} unit '{curr['Nama Barang']}'")
                        c_jml, c_aksi = st.columns(2)
                        j_potong = c_jml.number_input("Jumlah unit", 1, int(curr['Jumlah'])-1)
                        opsi = c_aksi.radio("Tindakan:", ["Pindah Lokasi", "Lapor Rusak"])
                        tujuan_baru = st.text_input("Lokasi Baru / Info Kerusakan")
                        
                        if st.form_submit_button("Konfirmasi Pecah"):
                            idx_asal = get_row_index(ws_inv, curr['Nama Barang'], curr['Lokasi'])
                            ws_inv.update_cell(idx_asal, 3, int(curr['Jumlah'] - j_potong))
                            n_lok = tujuan_baru if opsi == "Pindah Lokasi" else curr['Lokasi']
                            n_kon = curr['Kondisi'] if opsi == "Pindah Lokasi" else "Rusak Ringan"
                            ws_inv.append_row([curr['Nama Barang'], curr['Spesifikasi'], int(j_potong), n_lok, n_kon, "Tersedia", 0, tujuan_baru])
                            st.success("Berhasil dipecah!"); st.cache_data.clear(); time.sleep(1); st.rerun()
                else:
                    st.caption("Unit hanya ada 1, gunakan form utama di atas.")

            # 3. Fitur Hapus (HANYA ADMIN)
            if st.session_state['role'] == "admin":
                with st.expander("🗑️ Zona Bahaya (Hapus Aset)"):
                    with st.form("f_delete_asset"):
                        st.error("Hanya Admin yang bisa menghapus aset dari daftar permanen.")
                        alasan_hapus = st.text_input("Alasan Penghapusan")
                        if st.form_submit_button("Hapus Permanen"):
                            if alasan_hapus:
                                idx_h = get_row_index(ws_inv, curr['Nama Barang'], curr['Lokasi'])
                                ws_inv.delete_rows(idx_h)
                                try: sh.worksheet("Log").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), st.session_state['role'], f"HAPUS: {curr['Nama Barang']} - {alasan_hapus}"])
                                except: pass
                                st.success("Dihapus!"); st.cache_data.clear(); time.sleep(1); st.rerun()
                            else: st.warning("Alasan wajib diisi.")
            else:
                st.caption("🔒 *Fitur penghapusan hanya tersedia untuk Admin.*")
        else:
            st.info("Belum ada data inventaris.")

# --- 9. LOG KAS BULANAN & LAINNYA ---
elif menu == "📥 Kas Bulanan" and st.session_state['role'] == "admin":
    st.subheader("📥 Input Pembayaran Iuran")
    warga_options = sorted([f"{row['Nama']} ({row['Role']})" for _, row in df_warga.iterrows()]) if not df_warga.empty else []
    selected_display = st.selectbox("Pilih Nama Warga", warga_options)
    w_pilih = selected_display.split(" (")[0]
    mode = st.radio("Pilih Mode Alokasi Dana:", ["Paket Lengkap (50rb)", "Hanya Kas (15rb)", "Hanya Hadiah (35rb)", "Custom Nominal"], horizontal=True)
    n_val = 50000 if "Paket Lengkap" in mode else 15000 if "Hanya Kas" in mode else 35000 if "Hanya Hadiah" in mode else 0
    with st.form("f_kas", clear_on_submit=True):
        c_nom, c_thn, c_bln = st.columns([2, 1, 1])
        n = c_nom.number_input("Nominal Total yang Diterima (Rp)", value=n_val, step=5000)
        t_input = c_thn.selectbox("Tahun Mulai", range(2022, 2031), index=4)
        b_input = c_bln.selectbox("Bulan Mulai", bln_list)
        if st.form_submit_button("🚀 Proses & Simpan Pembayaran"):
            uang_sisa, bulan_idx, tahun_jalan, input_log = n, bln_list.index(b_input), t_input, []
            role_warga = df_warga[df_warga['Nama'] == w_pilih]['Role'].values[0] if not df_warga[df_warga['Nama'] == w_pilih].empty else "Main Warga"
            max_loop, loops = 60, 0
            while uang_sisa > 0 and loops < max_loop:
                loops += 1
                curr_month = bln_list[bulan_idx]
                df_curr = df_masuk[(df_masuk['Nama'] == w_pilih) & (df_masuk['Tahun'] == tahun_jalan) & (df_masuk['Bulan'] == curr_month)]
                kas_terbayar, hadiah_terbayar = df_curr['Kas'].sum(), df_curr['Hadiah'].sum()
                if mode == "Hanya Kas (15rb)": j_kas, j_hadiah = max(0, 15000 - kas_terbayar), 0
                elif mode == "Hanya Hadiah (35rb)": j_kas, j_hadiah = 0, max(0, 35000 - hadiah_terbayar)
                else: j_kas, j_hadiah = max(0, 15000 - kas_terbayar), max(0, 35000 - hadiah_terbayar)
                if j_kas <= 0 and j_hadiah <= 0:
                    bulan_idx += 1
                    if bulan_idx >= 12: bulan_idx = 0; tahun_jalan += 1
                    continue
                pakai_kas = min(uang_sisa, j_kas); uang_sisa -= pakai_kas
                pakai_hadiah = min(uang_sisa, j_hadiah); uang_sisa -= pakai_hadiah
                total_baris = pakai_kas + pakai_hadiah
                if total_baris > 0:
                    tipe_db = mode.split(" (")[0]
                    status_db = "PARTISIPASI" if role_warga == "Warga Support" else ("LUNAS" if (kas_terbayar + hadiah_terbayar + total_baris) >= 50000 else "BELUM LUNAS")
                    sh.worksheet("Pemasukan").append_row([datetime.now().strftime("%d/%m/%Y"), w_pilih, tahun_jalan, curr_month, int(total_baris), int(pakai_kas), int(pakai_hadiah), status_db, tipe_db])
                    input_log.append(f"{curr_month} {tahun_jalan}")
                bulan_idx += 1
                if bulan_idx >= 12: bulan_idx = 0; tahun_jalan += 1
            if input_log:
                st.success(f"✅ Berhasil diinput ke: {', '.join(input_log)}")
                st.cache_data.clear(); time.sleep(2); st.rerun()

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
