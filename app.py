import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIG HALAMAN ---
st.set_page_config(page_title="AR3 Mobile", layout="wide")

# --- KONEKSI GSPREAD (SERVICE ACCOUNT) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gspread_credentials"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# Buka spreadsheet (Ganti dengan ID Sheet kamu)
SHEET_ID = "1ebPvPCI7LUS98R4IhUr9LSFmY9JkvAMiTY92zhpQNoY"
sh = client.open_by_key(SHEET_ID)

# --- FUNGSI DATABASE ---
def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    # Pastikan kolom numerik benar-benar angka
    cols = ['Total', 'Kas', 'Hadiah', 'Jumlah']
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def save_to_cloud(sheet_name, df):
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    # Menulis kembali header dan data
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- LOAD DATA AWAL ---
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

# --- LOGIKA DASHBOARD ---
in_k = df_masuk['Kas'].sum() if not df_masuk.empty else 0
in_h = df_masuk['Hadiah'].sum() if not df_masuk.empty else 0
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum() if not df_keluar.empty else 0
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum() if not df_keluar.empty else 0

# --- UI DASHBOARD ---
st.title("📱 Kas AR3 Mobile")
c1, c2 = st.columns(2)
c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
st.divider()

# --- SIDEBAR MENU ---
menu = st.sidebar.selectbox("Pilih Menu", ["📊 Monitor", "📥 Input Pemasukan", "📤 Input Pengeluaran", "👥 Kelola Warga"])

# 1. MONITOR
if menu == "📊 Monitor":
    st.subheader("Histori Pemasukan")
    st.dataframe(df_masuk.tail(10), use_container_width=True)
    st.subheader("Histori Pengeluaran")
    st.dataframe(df_keluar.tail(10), use_container_width=True)

# 2. INPUT PEMASUKAN
elif menu == "📥 Input Pemasukan":
    st.subheader("Catat Iuran Warga")
    with st.form("form_masuk", clear_on_submit=True):
        nama = st.selectbox("Nama Warga", df_warga['Nama'].tolist())
        nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        submit = st.form_submit_button("Simpan Pemasukan")
        
        if submit and nom > 0:
            # Hitung Kas 30% Hadiah 70% (Contoh Logika)
            p_kas = nom * 0.3
            p_hadiah = nom * 0.7
            
            new_data = pd.DataFrame([{
                'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'Nama': nama,
                'Tahun': datetime.now().year,
                'Bulan': datetime.now().strftime("%B"),
                'Total': nom,
                'Kas': p_kas,
                'Hadiah': p_hadiah,
                'Status': 'LUNAS',
                'Tipe': 'Paket Lengkap'
            }])
            
            df_updated = pd.concat([df_masuk, new_data], ignore_index=True)
            save_to_cloud("Pemasukan", df_updated)
            st.success("Data iuran berhasil masuk cloud!")
            st.rerun()

# 3. INPUT PENGELUARAN
elif menu == "📤 Input Pengeluaran":
    st.subheader("Catat Pengeluaran")
    with st.form("form_keluar", clear_on_submit=True):
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah"])
        nom = st.number_input("Nominal", min_value=0)
        ket = st.text_input("Keterangan")
        if st.form_submit_button("Simpan Pengeluaran"):
            new_o = pd.DataFrame([{
                'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'Kategori': kat,
                'Jumlah': nom,
                'Keterangan': ket
            }])
            df_updated = pd.concat([df_keluar, new_o], ignore_index=True)
            save_to_cloud("Pengeluaran", df_updated)
            st.success("Pengeluaran tercatat!")
            st.rerun()

# 4. KELOLA WARGA
elif menu == "👥 Kelola Warga":
    st.subheader("Manajemen Anggota")
    with st.form("tambah_warga", clear_on_submit=True):
        nama_baru = st.text_input("Nama Lengkap")
        role_baru = st.selectbox("Role", ["Main Warga", "Warga Support"])
        if st.form_submit_button("Tambah"):
            if nama_baru:
                new_w = pd.DataFrame([{'Nama': nama_baru, 'Role': role_baru}])
                df_updated = pd.concat([df_warga, new_w], ignore_index=True)
                save_to_cloud("Warga", df_updated)
                st.success("Warga baru tersimpan!")
                st.rerun()
    st.table(df_warga)
