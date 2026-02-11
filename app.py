import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG HALAMAN ---
st.set_page_config(page_title="AR3 Mobile", layout="wide")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df_masuk = conn.read(worksheet="Pemasukan")
        df_keluar = conn.read(worksheet="Pengeluaran")
        df_warga = conn.read(worksheet="Warga")
        
        # Bersihkan data dari baris kosong
        df_masuk = df_masuk.dropna(how='all')
        df_keluar = df_keluar.dropna(how='all')
        df_warga = df_warga.dropna(how='all')
        
        return df_masuk, df_keluar, df_warga
    except Exception:
        # Jika gagal baca/tab belum ada, buat dataframe kosong dengan kolom lengkap
        df_m = pd.DataFrame(columns=['Tanggal', 'Nama', 'Tahun', 'Bulan', 'Total', 'Kas', 'Hadiah', 'Status', 'Tipe'])
        df_k = pd.DataFrame(columns=['Tanggal', 'Kategori', 'Jumlah', 'Keterangan'])
        df_w = pd.DataFrame(columns=['Nama', 'Role'])
        return df_m, df_k, df_w

def safe_sum(df, column):
    if not df.empty and column in df.columns:
        return pd.to_numeric(df[column], errors='coerce').sum()
    return 0

# --- LOAD DATA ---
df_masuk, df_keluar, df_warga = load_data()

# --- DASHBOARD ---
st.title("📱 AR3 Kas Manager")

in_k = safe_sum(df_masuk, 'Kas')
in_h = safe_sum(df_masuk, 'Hadiah')

out_k = 0
out_h = 0
if not df_keluar.empty and 'Kategori' in df_keluar.columns:
    out_k = pd.to_numeric(df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'], errors='coerce').sum()
    out_h = pd.to_numeric(df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'], errors='coerce').sum()

# Tampilan Ringkas untuk HP
c1, c2 = st.columns(2)
c1.metric("💰 KAS", f"Rp {in_k - out_k:,.0f}")
c2.metric("🎁 HADIAH", f"Rp {in_h - out_h:,.0f}")
st.divider()

# --- MENU UTAMA ---
menu = st.sidebar.selectbox("Pilih Menu", ["Dashboard", "Input Pemasukan", "Input Pengeluaran", "Kelola Warga"])

if menu == "Dashboard":
    st.subheader("Histori Terakhir")
    if not df_masuk.empty:
        st.write("Pemasukan:")
        st.dataframe(df_masuk.tail(5), use_container_width=True)
    else:
        st.info("Belum ada data.")

elif menu == "Input Pemasukan":
    if df_warga.empty:
        st.warning("Tambahkan nama warga dulu di menu 'Kelola Warga'")
    else:
        with st.form("form_bayar"):
            nama = st.selectbox("Nama Warga", df_warga['Nama'].tolist())
            nominal = st.number_input("Nominal Bayar", min_value=0, step=5000)
            submit = st.form_submit_button("Simpan Data")
            if submit:
                # Logika simpan sederhana ke Google Sheets
                new_data = pd.DataFrame([{
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Nama': nama,
                    'Total': nominal,
                    'Kas': nominal * 0.3, # Contoh alokasi 30%
                    'Hadiah': nominal * 0.7,
                    'Status': 'LUNAS'
                }])
                updated_df = pd.concat([df_masuk, new_data], ignore_index=True)
                conn.update(worksheet="Pemasukan", data=updated_df)
                st.success("Tersimpan!")
                st.rerun()

elif menu == "Kelola Warga":
    st.subheader("Daftar Warga")
    with st.form("tambah_warga"):
        nama_baru = st.text_input("Nama Lengkap")
        role_baru = st.selectbox("Role", ["Main Warga", "Warga Support"])
        if st.form_submit_button("Tambah"):
            new_warga = pd.concat([df_warga, pd.DataFrame([{'Nama': nama_baru, 'Role': role_baru}])], ignore_index=True)
            conn.update(worksheet="Warga", data=new_warga)
            st.rerun()
    st.table(df_warga)
