import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="KAS AR3 ONLINE", page_icon="🏦", layout="wide")

# --- 2. FUNGSI AMBIL DATA (MODE STABIL CSV) ---
def load_data():
    try:
        if "connections" not in st.secrets:
            st.error("Konfigurasi Secrets (Link Google Sheets) belum diisi!")
            st.stop()
            
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        clean_url = raw_url.split("/edit")[0].split("/view")[0]
        csv_base = f"{clean_url}/export?format=csv"
        
        # Baca tiap Sheet (Tab)
        df_m = pd.read_csv(f"{csv_base}&gid=0")
        df_k = pd.read_csv(f"{csv_base}&sheet=Pengeluaran")
        df_w = pd.read_csv(f"{csv_base}&sheet=Warga")
        
        # Bersihkan spasi di nama kolom
        df_m.columns = df_m.columns.str.strip()
        df_k.columns = df_k.columns.str.strip()
        df_w.columns = df_w.columns.str.strip()
        
        return df_m, df_k, df_w
    except Exception as e:
        st.error(f"⚠️ Gagal Memuat Data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 3. LOGIKA HITUNG PEMBAYARAN ---
def hitung_pembayaran(nama, nominal, thn, bln_mulai, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    try:
        idx = list_bulan.index(bln_mulai)
    except ValueError:
        idx = 0
        
    sisa = nominal
    data_baru = []
    
    while sisa > 0:
        bulan_skrg = list_bulan[idx]
        if role == "Main Warga":
            if not df_existing.empty:
                kondisi = (df_existing['Nama'] == nama) & (df_existing['Bulan'] == bulan_skrg) & (df_existing['Tahun'] == thn)
                sdh_bayar = df_existing[kondisi]['Total'].sum() if not df_existing[kondisi].empty else 0
                sdh_kas = df_existing[kondisi]['Kas'].sum() if not df_existing[kondisi].empty else 0
            else:
                sdh_bayar, sdh_kas = 0, 0
            
            if sdh_bayar < 50000:
                kekurangan = 50000 - sdh_bayar
                bayar_ini = min(sisa, kekurangan)
                porsi_kas = min(bayar_ini, max(0, 15000 - sdh_kas))
                porsi_hadiah = bayar_ini - porsi_kas
                
                # BAGIAN YANG TADI ERROR SUDAH DITUTUP DENGAN BENAR DI SINI
                data_baru.append({
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Nama': nama, 
                    'Tahun': thn, 
                    'Bulan': bulan_skrg,
                    'Total': bayar_ini, 
                    'Kas': porsi_kas, 
                    'Hadiah': porsi_hadiah,
                    'Status': "LUNAS" if (sdh_bayar + bayar_ini) >= 50000 else "CICIL",
                    'Tipe': "Paket Lengkap"
                })
                sisa -= bayar_ini
        else:
            # Warga Support
            data_baru.append({
                'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'Nama': nama, 
                'Tahun': thn, 
                'Bulan': bulan_skrg,
                'Total': sisa, 
                'Kas': sisa if tipe == "Hanya Kas" else 0,
                'Hadiah': sisa if tipe == "Hanya Hadiah" else 0,
                'Status': "SUPPORT", 
                'Tipe': tipe
            })
            sisa = 0
            
        idx += 1
        if idx > 11: 
            idx = 0
            thn += 1
        if thn > 2030: break
        
    return pd.DataFrame(data_baru)

# --- 4. MAIN INTERFACE ---
df_masuk, df_keluar, df_warga = load_data()

st.title("🏦 DASHBOARD KAS AR3")

# Metric Saldo
if not df_masuk.empty:
    in_k = df_masuk['Kas'].sum() if 'Kas' in df_masuk.columns else 0
    in_h = df_masuk['Hadiah'].sum() if 'Hadiah' in df_masuk.columns else 0
    out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum() if not df_keluar.empty else 0
    out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum() if not df_keluar.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
    c2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
    c3.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h)-(out_k+out_h):,.0f}")

st.divider()

menu = st.sidebar.radio("NAVIGASI", ["📥 Input Masuk", "📊 Laporan", "👥 Warga"])

if menu == "📥 Input Masuk":
    st.subheader("Input Pembayaran")
    if not df_warga.empty:
        with st.form("form_pembayaran", clear_on_submit=True):
            nama_p = st.selectbox("Pilih Nama", df_warga['Nama'].tolist())
            role_p = df_warga[df_warga['Nama'] == nama_p]['Role'].values[0]
            nom = st.number_input("Nominal (Rp)", min_value=0, step=5000)
            c1, c2 = st.columns(2)
            thn_p = c1.selectbox("Tahun", [2024, 2025, 2026], index=1)
            bln_p = c2.selectbox("Mulai Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            tipe_p = st.selectbox("Tipe", ["Paket Lengkap"] if role_p == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            
            submit = st.form_submit_button("Hitung")
            if submit:
                if nom > 0:
                    res = hitung_pembayaran(nama_p, nom, thn_p, bln_p, tipe_p, role_p, df_masuk)
                    st.success("Salin data di bawah ke Google Sheets:")
                    st.dataframe(res)
                else:
                    st.warning("Masukkan nominal.")
    else:
        st.warning("Data Warga kosong.")

elif menu == "📊 Laporan":
    st.subheader("Log Pemasukan Terakhir")
    st.dataframe(df_masuk.tail(10))

elif menu == "👥 Warga":
    st.subheader("Daftar Warga")
    st.table(df_warga)
