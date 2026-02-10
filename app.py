import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AR3 Online - Stabil", layout="wide", page_icon="🏦")

# --- KONEKSI DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Menggunakan metode pembacaan langsung agar anti-error 400
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = url.split("/edit")[0] + "/export?format=csv"
        
        # Membaca tiap tab dengan parameter sheet_name
        # Pastikan nama sheet di Google Sheets: Pemasukan, Pengeluaran, Warga
        df_m = pd.read_csv(f"{csv_url}&sheet=Pemasukan")
        df_k = pd.read_csv(f"{csv_url}&sheet=Pengeluaran")
        df_w = pd.read_csv(f"{csv_url}&sheet=Warga")
        
        # Bersihkan data kosong
        df_m = df_m.dropna(how='all')
        df_k = df_k.dropna(how='all')
        df_w = df_w.dropna(how='all')

        # Tambah kolom pembantu untuk sorting tanggal
        if not df_m.empty:
            df_m['Tanggal_Obj'] = pd.to_datetime(df_m['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        
        return df_m, df_k, df_w
    except Exception as e:
        st.error(f"Koneksi Gagal. Pastikan Spreadsheet sudah 'Anyone with the link' & Nama Tab Benar. Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def save_data(df_m, df_k, df_w):
    # Hapus kolom pembantu sebelum simpan ke Cloud
    df_m_save = df_m.drop(columns=['Tanggal_Obj'], errors='ignore')
    try:
        conn.update(worksheet="Pemasukan", data=df_m_save)
        conn.update(worksheet="Pengeluaran", data=df_k)
        conn.update(worksheet="Warga", data=df_w)
        st.cache_data.clear()
        st.toast("✅ Data Tersimpan ke Google Sheets!")
    except Exception as e:
        st.error(f"Gagal menyimpan ke Google Sheets: {e}")

# --- PROSES LOGIKA PEMBAYARAN ---
def proses_bayar(nama, nominal, thn, bln, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx_bln = list_bulan.index(bln)
    sisa = nominal
    data_baru = []
    
    while sisa > 0:
        curr_bln = list_bulan[idx_bln]
        if role == "Main Warga":
            kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == curr_bln) & (df_existing['Tahun'] == thn)
            sdh_bayar = df_existing[kondisi]['Total'].sum() if not df_existing[kondisi].empty else 0
            sdh_kas = df_existing[kondisi]['Kas'].sum() if not df_existing[kondisi].empty else 0

            if sdh_bayar >= 50000:
                pass # Sudah lunas, lanjut bulan depan
            else:
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
        if idx_bln > 11: 
            idx_bln = 0
            thn += 1
        if thn > 2030: break
    return pd.DataFrame(data_baru)

# --- LOAD DATA AWAL ---
df_masuk, df_keluar, df_warga = load_data()

# --- TAMPILAN DASHBOARD ---
st.title("📊 Dashboard Kas Majelis AR3")

if not df_masuk.empty:
    in_k = df_masuk['Kas'].sum()
    in_h = df_masuk['Hadiah'].sum()
    out_k = df_keluar['Jumlah'][df_keluar['Kategori'] == 'Kas'].sum() if not df_keluar.empty else 0
    out_h = df_keluar['Jumlah'][df_keluar['Kategori'] == 'Hadiah'].sum() if not df_keluar.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
    c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
    c3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")
else:
    st.info("Data belum tersedia. Pastikan Google Sheets sudah terisi header.")

st.divider()

# --- MENU NAVIGASI ---
menu = st.sidebar.radio("Navigasi Menu", ["📥 Input Pemasukan", "📤 Input Pengeluaran", "📊 Laporan", "👥 Kelola Warga", "📜 Log Transaksi"])

if menu == "📥 Input Pemasukan":
    st.subheader("Input Pembayaran Iuran")
    if not df_warga.empty:
        list_warga = sorted(df_warga['Nama'].tolist())
        nama_p = st.selectbox("Pilih Nama", list_warga)
        role_p = df_warga.loc[df_warga['Nama'] == nama_p, 'Role'].values[0]
        
        with st.form("form_in", clear_on_submit=True):
            st.info(f"Anggota: {nama_p} | Role: {role_p}")
            nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            tipe = st.selectbox("Alokasi", ["Paket Lengkap"] if role_p == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            thn = st.selectbox("Tahun", [2024, 2025, 2026, 2027], index=2)
            bln = st.selectbox("Mulai Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            
            if st.form_submit_button("Simpan Data"):
                new_data = proses_bayar(nama_p, nom, thn, bln, tipe, role_p, df_masuk)
                if not new_data.empty:
                    df_masuk = pd.concat([df_masuk, new_data], ignore_index=True)
                    save_data(df_masuk, df_keluar, df_warga)
                    st.rerun()
    else:
        st.warning("Tambahkan data warga dulu di menu 'Kelola Warga'")

elif menu == "📤 Input Pengeluaran":
    st.subheader("Catat Pengeluaran")
    with st.form("form_out", clear_on_submit=True):
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah"])
        nom = st.number_input("Nominal", min_value=0)
        ket = st.text_input("Keterangan Keperluan")
        if st.form_submit_button("Potong Saldo"):
            new_out = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat, 'Jumlah': nom, 'Keterangan': ket}])
            df_keluar = pd.concat([df_keluar, new_out], ignore_index=True)
            save_data(df_masuk, df_keluar, df_warga)
            st.rerun()

elif menu == "📊 Laporan":
    st.subheader("Monitoring Kelunasan")
    thn_sel = st.selectbox("Tahun Laporan", [2024, 2025, 2026, 2027], index=2)
    if not df_masuk.empty:
        df_yr = df_masuk[df_masuk['Tahun'] == thn_sel]
        if not df_yr.empty:
            rekap = df_yr.pivot_table(index='Nama', columns='Bulan', values='Total', aggfunc='sum').fillna(0)
            st.dataframe(rekap.style.highlight_between(left=50000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
        else:
            st.info("Belum ada data di tahun ini")

elif menu == "👥 Kelola Warga":
    st.subheader("Database Anggota")
    with st.form("form_warga", clear_on_submit=True):
        n_br = st.text_input("Nama Warga Baru")
        r_br = st.selectbox("Role", ["Main Warga", "Warga Support"])
        if st.form_submit_button("Tambah Warga"):
            df_warga = pd.concat([df_warga, pd.DataFrame([{'Nama': n_br, 'Role': r_br}])], ignore_index=True)
            save_data(df_masuk, df_keluar, df_warga)
            st.rerun()
    st.table(df_warga)

elif menu == "📜 Log Transaksi":
    st.subheader("Riwayat Transaksi")
    t1, t2 = st.tabs(["Pemasukan", "Pengeluaran"])
    with t1:
        if not df_masuk.empty:
            st.dataframe(df_masuk.sort_values(by='Tanggal_Obj', ascending=False).drop(columns=['Tanggal_Obj']), use_container_width=True)
    with t2:
        if not df_keluar.empty:
            st.dataframe(df_keluar.sort_values(by='Tanggal_Obj', ascending=False), use_container_width=True)
