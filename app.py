import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- KONEKSI GSPREAD ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gspread_credentials"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# Buka spreadsheet berdasarkan ID atau URL
SHEET_ID = "1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE"
sh = client.open_by_key(SHEET_ID)

def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def save_data(sheet_name, df):
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- LOAD DATA ---
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")

st.title("📱 Kas AR3 - Cloud Mode")

menu = st.sidebar.selectbox("Menu", ["Kelola Warga", "Monitor"])

if menu == "Kelola Warga":
    st.subheader("Manajemen Anggota")
    with st.form("tambah_warga"):
        nama_baru = st.text_input("Nama Lengkap")
        role_baru = st.selectbox("Role", ["Main Warga", "Warga Support"])
        if st.form_submit_button("Simpan ke Cloud"):
            if nama_baru:
                # Tambah data
                new_row = pd.DataFrame([{'Nama': nama_baru, 'Role': role_baru}])
                df_updated = pd.concat([df_warga, new_row], ignore_index=True)
                
                # Simpan (GSpread sangat stabil untuk ini)
                save_data("Warga", df_updated)
                st.success("Tersimpan!")
                st.rerun()

    st.table(df_warga)
