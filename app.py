import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="KAS AR3 ONLINE", page_icon="🏦", layout="wide")

# --- 2. FUNGSI AMBIL DATA (MODE STABIL CSV) ---
def load_data():
    try:
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        clean_url = raw_url.split("/edit")[0].split("/view")[0]
        csv_base = f"{clean_url}/export?format=csv"
        
        df_m = pd.read_csv(f"{csv_base}&gid=0")
        df_k = pd.read_csv(f"{csv_base}&sheet=Pengeluaran")
        df_w = pd.read_csv(f"{csv_base}&sheet=Warga")
        
        # Bersihkan spasi di nama kolom agar tidak KeyError
        df_m.columns = df_m.columns.str.strip()
        df_k.columns = df_k.columns.str.strip()
        df_w.columns = df_w.columns.str.strip()
        
        return df_m, df_k, df_w
    except Exception as e:
        st.error(f"Gagal Sinkron GSheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 3. LOGIKA HITUNG OTOMATIS ---
def hitung_otomatis(nama, nominal, thn, bln_mulai, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx = list_bulan.index(bln_mulai)
    sisa = nominal
    data_baru = []
    
    while sisa > 0:
        bulan_skrg = list_bulan[idx]
        if role == "Main Warga":
            kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == bulan_skrg) & (df_existing['Tahun'] == thn)
            sdh_bayar = df_existing[kondisi]['Total'].sum() if not df_existing[kondisi].empty else 0
            sdh_kas = df_existing[kondisi]['Kas'].sum() if not df_existing[kondisi].empty else 0
            
            if sdh_bayar < 50000:
                kekurangan = 50000 - sdh_bayar
                bayar_ini = min(sisa, kekurangan)
                porsi_kas = min(bayar_ini, max(0, 15000 - sdh_kas))
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
            data_baru.append({'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Nama': nama, 'Tahun': thn, 'Bulan': bulan_skrg, 'Total': sisa, 'Kas': sisa if tipe == "Hanya Kas" else 0, 'Hadiah': sisa if tipe == "Hanya Hadiah" else 0, 'Status': "SUPPORT", 'Tipe': tipe})
            sisa = 0
            
        idx += 1
        if idx > 11: idx = 0;
