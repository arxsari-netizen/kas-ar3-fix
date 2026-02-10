import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="KAS AR3 ONLINE", page_icon="🏦", layout="wide")

# --- 2. FUNGSI AMBIL DATA (MODE STABIL CSV) ---
def load_data():
    try:
        # Ambil URL dari Secrets
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        clean_url = raw_url.split("/edit")[0].split("/view")[0]
        csv_base = f"{clean_url}/export?format=csv"
        
        # Baca tiap Sheet (Pemasukan di gid=0, sisanya pakai nama sheet)
        df_m = pd.read_csv(f"{csv_base}&gid=0")
        df_k = pd.read_csv(f"{csv_base}&sheet=Pengeluaran")
        df_w = pd.read_csv(f"{csv_base}&sheet=Warga")
        
        # Konversi Tanggal untuk sortir
        df_m['Tanggal_Obj'] = pd.to_datetime(df_m['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        
        return df_m, df_k, df_w
    except Exception as e:
        st.error(f"Gagal Sinkron GSheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 3. LOGIKA PEMBAGIAN KAS & HADIAH ---
def hitung_otomatis(nama, nominal, thn, bln_mulai, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx = list_bulan.index(bln_mulai)
    sisa = nominal
    data_baru = []
    
    while sisa > 0:
        bulan_skrg = list_bulan[idx]
        if role == "Main Warga":
            # Cek iuran bulan ini yang sudah masuk
            kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == bulan_skrg) & (df_existing['Tahun'] == thn)
            sdh_bayar = df_existing[kondisi]['Total'].sum() if not df_existing[kondisi].empty else 0
            sdh_kas = df_existing[kondisi]['Kas'].sum() if not df_existing[kondisi].empty else 0
            
            if sdh_bayar < 50000:
                kekurangan = 50000 - sdh_bayar
                bayar_ini = min(sisa, kekurangan)
                
                # Jatah Kas max 15rb/bulan
                jatah_kas = max(0, 15000 - sdh_kas)
                porsi_kas = min(bayar_ini, jatah_kas)
                porsi_hadiah = bayar_ini - porsi_kas
                
                data_baru.append({
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Nama': nama, 'Tahun': thn, 'Bulan': bulan_skrg,
                    'Total': bayar_ini, 'Kas': porsi_kas, 'Hadiah': porsi_hadiah,
                    'Status': "LUNAS" if (sdh_bayar + bayar_ini) >= 50000 else "CICIL",
                    'Tipe': "Paket Lengkap"
                })
                sisa -= bayar_ini
        else:
            # Warga Support
            data_baru.append({
                'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'Nama': nama, 'Tahun': thn, 'Bulan': bulan_skrg,
                'Total': sisa, 'Kas': sisa if tipe == "Hanya Kas" else 0,
                'Hadiah': sisa if tipe == "Hanya Hadiah" else 0,
                'Status': "SUPPORT", 'Tipe': tipe
            })
            sisa = 0
            
        idx += 1
        if idx > 11: idx = 0; thn += 1
        if thn > 2030: break
    return pd.DataFrame(data_baru)

# --- 4. MAIN APP ---
df_masuk, df_keluar, df_warga = load_data()

st.title("🏦 KAS AR3 ONLINE")

# Bagian Saldo (Metric)
if not df_masuk.empty:
    in_k = df_masuk['Kas'].sum()
    in_h = df_masuk['Hadiah'].sum()
    out_k = df_keluar['Jumlah'][df_keluar['Kategori'] == 'Kas'].sum() if not df_keluar.empty else 0
    out_h = df_keluar['Jumlah'][df_keluar['Kategori'] == 'Hadiah'].sum() if not df_keluar.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
    c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
    c3.metric("🏦 TOTAL DANA", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")

st.divider()

# Sidebar Navigasi
menu = st.sidebar.radio("MENU UTAMA", ["📥 Input Masuk", "📤 Input Keluar", "📊 Laporan", "👥 Warga", "📜 Log"])

if menu == "📥 Input Masuk":
    st.subheader("📥 Input Pemasukan Iuran")
    if not df_warga.empty:
        with st.form("form_masuk", clear_on_submit=True):
            nama_p = st.selectbox("Pilih Nama", df_warga['Nama'].tolist())
            role_p = df_warga[df_warga['Nama'] == nama_p]['Role'].values[0]
            nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            c1, c2 = st.columns(2)
            thn = c1.selectbox("Tahun", [2024, 2025, 2026], index=1)
            bln = c2.selectbox("Mulai Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            tipe = st.selectbox("Tipe", ["Paket Lengkap"] if role_p == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            
            if st.form_submit_button("Simpan Ke Google Sheets"):
                st.info("Silakan salin data di bawah ke Google Sheets secara manual karena mode ini 'Read-Only'.")
                res = hitung_otomatis(nama_p, nom, thn, bln, tipe, role_p, df_masuk)
                st.dataframe(res)
    else:
        st.warning("Data Warga masih kosong.")

elif menu == "📊 Laporan":
    st.subheader
