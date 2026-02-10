import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="AR3 SMART KAS", page_icon="🏦", layout="wide")

# CSS untuk tampilan ala aplikasi Mobile
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stMetricValue"] { color: #1f77b4; font-size: 1.5rem !important; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #1f77b4; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_csv_url():
    # Mengambil URL dari secrets dan mengubahnya menjadi format CSV ekspor
    try:
        base_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return base_url.split("/edit")[0] + "/export?format=csv"
    except:
        st.error("Konfigurasi Secrets belum benar!")
        st.stop()

@st.cache_data(ttl=60) # Cache 1 menit agar kencang
def load_all_data():
    csv_base = get_csv_url()
    try:
        # Load dengan penanganan error kolom
        m = pd.read_csv(f"{csv_base}&sheet=Pemasukan")
        k = pd.read_csv(f"{csv_base}&sheet=Pengeluaran")
        w = pd.read_csv(f"{csv_base}&sheet=Warga")
        
        # Bersihkan spasi di nama kolom
        for df in [m, k, w]:
            df.columns = df.columns.str.strip()
            
        return m.dropna(how='all'), k.dropna(how='all'), w.dropna(how='all')
    except Exception as e:
        st.error(f"Gagal membaca tab. Pastikan nama tab (Pemasukan, Pengeluaran, Warga) benar. Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def sync_to_cloud(df_m, df_k, df_w):
    try:
        conn.update(worksheet="Pemasukan", data=df_m)
        conn.update(worksheet="Pengeluaran", data=df_k)
        conn.update(worksheet="Warga", data=df_w)
        st.cache_data.clear()
        st.toast("🚀 Sinkronisasi Berhasil!")
    except Exception as e:
        st.error(f"Gagal Simpan: {e}")

# --- 3. LOGIKA PEMBAYARAN PINTAR ---
def hitung_pembayaran(nama, total_bayar, thn, bln_mulai, tipe, role, df_m):
    list_bln = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx = list_bln.index(bln_mulai)
    sisa = total_bayar
    entries = []

    while sisa > 0:
        bulan_skrg = list_bln[idx]
        if role == "Main Warga":
            # Cek riwayat untuk bulan ini
            mask = (df_m['Nama'] == nama) & (df_m['Bulan'] == bulan_skrg) & (df_m['Tahun'] == thn)
            terbayar = df_m[mask]['Total'].sum() if not df_m[mask].empty else 0
            terbayar_kas = df_m[mask]['Kas'].sum() if not df_m[mask].empty else 0
            
            if terbayar < 50000:
                kekurangan = 50000 - terbayar
                alokasi = min(sisa, kekurangan)
                
                # Alokasi Kas (max 15rb per bulan)
                jatah_kas = max(0, 15000 - terbayar_kas)
                porsi_kas = min(alokasi, jatah_kas)
                porsi_hadiah = alokasi - porsi_kas
                
                entries.append({
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Nama': nama, 'Tahun': thn, 'Bulan': bulan_skrg,
                    'Total': alokasi, 'Kas': porsi_kas, 'Hadiah': porsi_hadiah,
                    'Status': "LUNAS" if (terbayar + alokasi) >= 50000 else "CICIL",
                    'Tipe': "Paket Lengkap"
                })
                sisa -= alokasi
        else:
            # Warga Support: Langsung habiskan sisa
            entries.append({
                'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'Nama': nama, 'Tahun': thn, 'Bulan': bulan_skrg,
                'Total': sisa, 'Kas': sisa if tipe == "Hanya Kas" else 0,
                'Hadiah': sisa if tipe == "Hanya Hadiah" else 0,
                'Status': "SUPPORT", 'Tipe': tipe
            })
            sisa = 0
            
        idx += 1
        if idx > 11: 
            idx = 0; thn += 1
        if thn > 2030: break
    return pd.DataFrame(entries)

# --- 4. MAIN INTERFACE ---
df_m, df_k, df_w = load_all_data()

st.title("🏦 AR3 Smart Dashboard")

# Row 1: Saldo Utama
if not df_m.empty:
    k_in = df_m['Kas'].sum(); h_in = df_m['Hadiah'].sum()
    k_out = df_k[df_k['Kategori'] == 'Kas']['Jumlah'].sum() if not df_k.empty else 0
    h_out = df_k[df_k['Kategori'] == 'Hadiah']['Jumlah'].sum() if not df_k.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Saldo Kas", f"Rp {k_in - k_out:,.0f}")
    c2.metric("🎁 Saldo Hadiah", f"Rp {h_in - h_out:,.0f}")
    c3.metric("💳 Total Dana", f"Rp {(k_in+h_in)-(k_out+h_out):,.0f}")

st.divider()

# Sidebar Menu dengan Ikon
with st.sidebar:
    st.header("MENU UTAMA")
    menu = st.radio("Pilih Navigasi:", ["💵 Pemasukan", "💸 Pengeluaran", "📊 Laporan Iuran", "👥 Data Warga", "📑 Log"])

if menu == "💵 Pemasukan":
    st.subheader("Input Iuran Anggota")
    if not df_w.empty:
        with st.form("form_in"):
            nama = st.selectbox("Pilih Anggota", df_w['Nama'].unique())
            role = df_w[df_w['Nama'] == nama]['Role'].values[0]
            nom = st.number_input("Nominal Bayar (Rp)", min_value=0, step=10000)
            c1, c2 = st.columns(2)
            thn = c1.selectbox("Tahun", [2025, 2026, 2027], index=1)
            bln = c2.selectbox("Mulai Bulan", ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
            tipe = st.selectbox("Alokasi", ["Paket Lengkap"] if role == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            
            if st.form_submit_button("SINKRON PEMBAYARAN"):
                new_data = hitung_pembayaran(nama, nom, thn, bln, tipe, role, df_m)
                if not new_data.empty:
                    df_m = pd.concat([df_m, new_data], ignore_index=True)
                    sync_to_cloud(df_m, df_k, df_w)
                    st.rerun()
    else:
        st.warning("Silakan isi data warga terlebih dahulu.")

elif menu == "💸 Pengeluaran":
    st.subheader("Catat Pengeluaran Majelis")
    with st.form("form_out"):
        kat = st.radio("Ambil Dari", ["Kas", "Hadiah"])
        jml = st.number_input("Nominal Keluar", min_value=0)
        ket = st.text_input("Keterangan/Keperluan")
        if st.form_submit_button("POTONG SALDO"):
            entry_k = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat, 'Jumlah': jml, 'Keterangan': ket}])
            df_k = pd.concat([df_k, entry_k], ignore_index=True)
            sync_to_cloud(df_m, df_k, df_w)
            st.rerun()

elif menu == "📊 Laporan Iuran":
    st.subheader("Status Kelunasan Iuran")
    t_sel = st.selectbox("Tahun Laporan", [2025, 2026, 2027], index=1)
    if not df_m.empty:
        df_t = df_m[df_m['Tahun'] == t_sel]
        if not df_t.empty:
            pivot = df_t.pivot_table(index='Nama', columns='Bulan', values='Total', aggfunc='sum').fillna(0)
            # Reorder columns sesuai urutan bulan
            blns = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            cols = [b for b in blns if b in pivot.columns]
            st.dataframe(pivot[cols].style.format("{:,.0f}").background_gradient(cmap="Greens"), use_container_width=True)
        else:
            st.info("Belum ada data transaksi di tahun ini.")

elif menu == "👥 Data Warga":
    st.subheader("Manajemen Anggota")
    with st.expander("➕ Tambah Warga Baru"):
        with st.form("f_w"):
            nw = st.text_input("Nama Lengkap")
            rw = st.selectbox("Status", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Simpan Anggota"):
                df_w = pd.concat([df_w, pd.DataFrame([{'Nama': nw, 'Role': rw}])], ignore_index=True)
                sync_to_cloud(df_m, df_k, df_w)
                st.rerun()
    st.table(df_w)

elif menu == "📑 Log":
    st.subheader("Riwayat Transaksi Terakhir")
    tab1, tab2 = st.tabs(["Pemasukan", "Pengeluaran"])
    with tab1: st.dataframe(df_m.sort_index(ascending=False), use_container_width=True)
    with tab2: st.dataframe(df_k.sort_index(ascending=False), use_container_width=True)
