import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG HALAMAN ---
st.set_page_config(page_title="AR3 Mobile", layout="wide")

# --- KONEKSI GOOGLE SHEETS ---
# Pastikan URL sheet sudah dimasukkan di .streamlit/secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Menghapus ttl="0" sementara untuk memastikan koneksi stabil
        df_masuk = conn.read(worksheet="Pemasukan")
        df_keluar = conn.read(worksheet="Pengeluaran")
        df_warga = conn.read(worksheet="Warga")
    
  # Konversi tanggal agar aman
        df_masuk['Tanggal_Obj'] = pd.to_datetime(df_masuk['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        df_keluar['Tanggal_Obj'] = pd.to_datetime(df_keluar['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        return df_masuk, df_keluar, df_warga
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.info("Pastikan nama tab di Google Sheets adalah: Pemasukan, Pengeluaran, dan Warga")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
def save_data(df_m, df_k, df_w):
    # Menghapus kolom temporary sebelum simpan ke cloud
    df_m_save = df_m.drop(columns=['Tanggal_Obj'], errors='ignore')
    df_k_save = df_k.drop(columns=['Tanggal_Obj'], errors='ignore')
    
    conn.update(worksheet="Pemasukan", data=df_m_save)
    conn.update(worksheet="Pengeluaran", data=df_k_save)
    conn.update(worksheet="Warga", data=df_w)
    st.cache_data.clear()

# --- LOGIKA BAYAR ---
def proses_bayar(nama, nominal, thn, bln, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    try:
        idx_bln = list_bulan.index(bln)
    except ValueError:
        idx_bln = 0
        
    sisa = nominal
    data_baru = []

    while sisa > 0:
        curr_bln = list_bulan[idx_bln]
        if role == "Main Warga":
            kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == curr_bln) & (df_existing['Tahun'] == thn)
            sdh_bayar = df_existing[kondisi]['Total'].sum()
            sdh_kas = df_existing[kondisi]['Kas'].sum()

            if sdh_bayar < 50000:
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

# --- DASHBOARD ATAS (VERSI AMAN) ---
st.title("📱 Kas AR3 Mobile")

# Fungsi pembantu untuk hitung sum yang aman jika kolom/data kosong
def safe_sum(df, column):
    if not df.empty and column in df.columns:
        return pd.to_numeric(df[column], errors='coerce').sum()
    return 0

in_k = safe_sum(df_masuk, 'Kas')
in_h = safe_sum(df_masuk, 'Hadiah')

# Filter pengeluaran dengan aman
out_k = 0
out_h = 0
if not df_keluar.empty and 'Kategori' in df_keluar.columns and 'Jumlah' in df_keluar.columns:
    out_k = pd.to_numeric(df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'], errors='coerce').sum()
    out_h = pd.to_numeric(df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'], errors='coerce').sum()

# Tampilan Metric
c1, c2 = st.columns(2)
c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
st.divider()

if menu == "Input Masuk":
    st.subheader("📥 Tambah Pemasukan")
    nama_p = st.selectbox("Nama", sorted(df_warga['Nama'].tolist()))
    role_p = df_warga.loc[df_warga['Nama'] == nama_p, 'Role'].values[0]
    
    with st.form("form_masuk"):
        nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        thn = st.selectbox("Tahun Mulai", [2024, 2025, 2026])
        bln = st.selectbox("Bulan Mulai", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        if st.form_submit_button("Simpan"):
            res = proses_bayar(nama_p, nom, thn, bln, "Paket Lengkap", role_p, df_masuk)
            if not res.empty:
                df_masuk = pd.concat([df_masuk, res], ignore_index=True)
                save_data(df_masuk, df_keluar, df_warga)
                st.success("Data Berhasil di Sinkron ke Cloud!")
                st.rerun()

elif menu == "Input Keluar":
    st.subheader("📤 Catat Pengeluaran")
    with st.form("form_keluar"):
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah"])
        nom = st.number_input("Nominal", min_value=0)
        ket = st.text_input("Keterangan")
        if st.form_submit_button("Potong Saldo"):
            new_o = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat, 'Jumlah': nom, 'Keterangan': ket}])
            df_keluar = pd.concat([df_keluar, new_o], ignore_index=True)
            save_data(df_masuk, df_keluar, df_warga)
            st.rerun()

elif menu == "Monitor":
    st.subheader("📊 Laporan")
    st.write("Histori Pemasukan Terakhir")
    st.dataframe(df_masuk.tail(5), use_container_width=True)
