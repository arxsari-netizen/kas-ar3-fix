import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kas Majelis AR3 Online", layout="wide")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Membaca data dari Google Sheets (Pastikan nama tab/sheet di Google Sheets sama persis)
        df_masuk = conn.read(worksheet="Pemasukan", ttl=0)
        df_keluar = conn.read(worksheet="Pengeluaran", ttl=0)
        df_warga = conn.read(worksheet="Warga", ttl=0)
        
        # Konversi tanggal agar bisa diurutkan
        df_masuk['Tanggal_Obj'] = pd.to_datetime(df_masuk['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        df_keluar['Tanggal_Obj'] = pd.to_datetime(df_keluar['Tanggal'], format="%d/%m/%Y %H:%M", errors='coerce')
        
        return df_masuk, df_keluar, df_warga
    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Pastikan Nama Sheet & URL benar. Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def save_data(df_m, df_k, df_w):
    # Fungsi untuk menyimpan kembali ke Google Sheets
    try:
        conn.update(worksheet="Pemasukan", data=df_m)
        conn.update(worksheet="Pengeluaran", data=df_k)
        conn.update(worksheet="Warga", data=df_w)
        st.cache_data.clear()
        st.success("Data berhasil disinkronkan ke Google Sheets!")
    except Exception as e:
        st.error(f"Gagal menyimpan ke Google Sheets: {e}")

# --- LOGIKA BAYAR ---
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
        if idx_bln > 11: idx_bln = 0; thn += 1
        if thn > 2030: break
    return pd.DataFrame(data_baru)

# --- JALANKAN APLIKASI ---
df_masuk, df_keluar, df_warga = load_data()

st.title("🏦 Kas Majelis AR3 Online")

if not df_masuk.empty:
    in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
    out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum() if not df_keluar.empty else 0
    out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum() if not df_keluar.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
    c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
    c3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")

st.divider()

# Tambahkan navigasi menu di sini (Input Pemasukan, Pengeluaran, dll.)
# Gunakan fungsi save_data(df_masuk, df_keluar, df_warga) setiap kali ada perubahan data.
