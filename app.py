import streamlit as st
import pandas as pd

# --- KONFIGURASI ---
st.set_page_config(page_title="KAS AR3 STABIL", layout="wide")

def get_url():
    # Ambil link dari secrets
    try:
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # Membersihkan link secara otomatis jika user copy paste sembarangan
        clean_id = raw_url.split("/d/")[1].split("/")[0]
        return f"https://docs.google.com/spreadsheets/d/{clean_id}/export?format=csv"
    except Exception as e:
        st.error(f"❌ Link di Secrets Salah Format! Error: {e}")
        st.stop()

# --- PROSES BACA DATA ---
def load_data():
    csv_base = get_url()
    try:
        # Kita baca Tab pertama (Pemasukan) lewat gid=0
        df_pemasukan = pd.read_csv(f"{csv_base}&gid=0")
        
        # Kita baca Tab Warga (Pastikan nama sheet di GSheets adalah 'Warga')
        # Jika gid gagal, kita gunakan nama sheet
        df_warga = pd.read_csv(f"{csv_base}&sheet=Warga")
        
        return df_pemasukan, df_warga
    except Exception as e:
        st.warning("⚠️ Gagal koneksi ke Google Sheets. Cek apakah sudah 'Anyone with the link can view'.")
        st.info(f"Detail error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- MAIN APP ---
st.title("🏦 Dashboard Kas AR3")

df_p, df_w = load_data()

if not df_w.empty:
    st.success("✅ Koneksi Berhasil!")
    st.write("### Daftar Warga dari Google Sheets:")
    st.dataframe(df_w, use_container_width=True)
else:
    st.error("❌ Data tidak terbaca. Pastikan Spreadsheet sudah di-SHARE ke 'Anyone with the link' sebagai VIEW.")
