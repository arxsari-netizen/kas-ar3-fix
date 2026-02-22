import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. CONFIG HALAMAN ---
st.set_page_config(
    page_title="AR-ROYHAAN 3 KAS & EVENT",
    page_icon="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png",
    layout="wide"
)

# --- 2. CSS GLOBAL ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #D4AF37; padding: 15px; border-radius: 12px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #D4AF37 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEM LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None

def login():
    _, col_mid, _ = st.columns([0.1, 1, 0.1])
    with col_mid:
        st.markdown(f"""
            <div style="text-align: center; border: 2px solid #D4AF37; padding: 20px; border-radius: 15px; background: white;">
                <img src="https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png" width="60">
                <h3 style="margin:10px 0 0 0;">AR-ROYHAAN 3</h3>
                <p style="color:#B8860B; font-weight:700;">MANAGEMENT KAS & EVENT</p>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk Ke Aplikasi"):
                if "users" in st.secrets:
                    u_data = st.secrets["users"]
                    if user == u_data.get("admin_user") and pwd == u_data.get("admin_password"):
                        st.session_state.update({"logged_in": True, "role": "admin"})
                        st.rerun()
                    elif user == u_data.get("warga_user") and pwd == u_data.get("warga_password"):
                        st.session_state.update({"logged_in": True, "role": "user"})
                        st.rerun()
                    else: st.error("Username/Password salah")

if not st.session_state['logged_in']:
    login()
    st.stop()

# --- 4. LOGIKA DATA ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gspread_credentials"], scopes=scope)
client = gspread.authorize(creds)
sh = client.open_by_key("1i3OqFAeFYJ7aXy0QSS0IUF9r_yp3pwqNb7tJ8-CEXQE")

@st.cache_data(ttl=300)
def load_data(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    df = pd.DataFrame(worksheet.get_all_records())
    numeric_cols = ['Total', 'Kas', 'Hadiah', 'Jumlah', 'Tahun']
    for col in numeric_cols:
        if col in df.columns: 
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def clear_cache(): st.cache_data.clear()

def append_to_cloud(sheet_name, df_new):
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_rows(df_new.values.tolist())
    clear_cache()

def rewrite_cloud(sheet_name, df_full):
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df_full.columns.values.tolist()] + df_full.values.tolist())
    clear_cache()

def proses_bayar(nama, nominal, thn, bln, tipe, role, df_existing):
    list_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    idx_bln = list_bulan.index(bln)
    sisa, data_baru = nominal, []
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
        if idx_bln > 11: idx_bln = 0; thn += 1
        if thn > 2030: break
    return pd.DataFrame(data_baru)

# LOAD DATA AWAL
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")
df_event = load_data("Event")

# --- 5. SIDEBAR & NAVIGASI (LOCK FIX) ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/arxsari-netizen/kas-ar3-fix/main/AR%20ROYHAAN.png", width=100)
    st.markdown(f"**👤 User: {st.session_state['role'].upper()}**")
    st.divider()
    list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📜 Log"]
    menu = st.radio("MENU UTAMA", list_menu)
    st.divider()
    if st.button("🔄 Refresh Data"): clear_cache(); st.rerun()
    if st.button("🚪 Logout"): st.session_state.clear(); st.rerun()

# --- 6. DASHBOARD METRIK ---
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()
in_ev_total = df_event['Jumlah'].sum() if not df_event.empty else 0
out_ev_total = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum() if not df_keluar.empty else 0
saldo_event_bersih = in_ev_total - out_ev_total

st.markdown(f"## 🏦 MANAGEMENT KEUANGAN")
m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 SALDO KAS (15rb)", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH (35rb)", f"Rp {in_h - out_h:,.0f}")
m3.metric("🎭 SALDO EVENT", f"Rp {saldo_event_bersih:,.0f}")
m4.metric("🏧 TOTAL CASH", f"Rp {(in_k+in_h+in_ev_total)-(out_k+out_h+out_ev_total):,.0f}")
st.divider()

# --- 7. KONTEN MENU ---

if menu == "📊 Laporan":
    st.subheader("📋 Laporan Keuangan Terpadu")
    tab1, tab2, tab3 = st.tabs(["💰 Kas & Hadiah Bulanan", "🎭 Detail Event", "📤 Pengeluaran"])
    
    with tab1:
        thn_lap = st.selectbox("Pilih Tahun", list(range(2022, 2031)), index=4)
        df_yr = df_masuk[df_masuk['Tahun'] == thn_lap]
        
        bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        if not df_yr.empty:
            # TABEL 1: KHUSUS KAS (15rb)
            st.markdown("#### 🟢 Tabel Kas (Wajib 15rb/bulan)")
            rk_kas = df_yr.pivot_table(index='Nama', columns='Bulan', values='Kas', aggfunc='sum').fillna(0)
            cols_kas = [b for b in bln_order if b in rk_kas.columns]
            st.dataframe(rk_kas[cols_kas].style.highlight_between(left=15000, color='#d4edda').format("{:,.0f}"), use_container_width=True)
            
            st.divider()
            
            # TABEL 2: KHUSUS HADIAH (35rb)
            st.markdown("#### 🟡 Tabel Hadiah (Wajib 35rb/bulan)")
            rk_hadi = df_yr.pivot_table(index='Nama', columns='Bulan', values='Hadiah', aggfunc='sum').fillna(0)
            cols_hadi = [b for b in bln_order if b in rk_hadi.columns]
            st.dataframe(rk_hadi[cols_hadi].style.highlight_between(left=35000, color='#fff3cd').format("{:,.0f}"), use_container_width=True)
        else:
            st.info("Belum ada data pemasukan di tahun ini.")

    with tab2:
        if not df_event.empty:
            ev_sel = st.selectbox("Pilih Event", df_event['Nama Event'].unique())
            e_in = df_event[df_event['Nama Event'] == ev_sel]['Jumlah'].sum()
            e_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(ev_sel, na=False))]['Jumlah'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Iuran Masuk", f"Rp {e_in:,.0f}")
            c2.metric("Belanja Event", f"Rp {e_out:,.0f}")
            c3.metric("Sisa Saldo", f"Rp {e_in - e_out:,.0f}")
            st.write(f"**Penyumbang {ev_sel}:**")
            st.dataframe(df_event[df_event['Nama Event'] == ev_sel][['Tanggal', 'Nama', 'Jumlah', 'Keterangan']], use_container_width=True)
        else:
            st.info("Data event masih kosong.")

    with tab3:
        st.write("### 📤 Riwayat Pengeluaran")
        kat_f = st.multiselect("Filter Dana:", ["Kas", "Hadiah", "Event"], default=["Kas", "Hadiah", "Event"])
        st.dataframe(df_keluar[df_keluar['Kategori'].isin(kat_f)].sort_values('Tanggal', ascending=False), use_container_width=True)

elif menu == "📥 Kas Bulanan":
    st.subheader("📥 Input Pembayaran Kas")
    if not df_warga.empty:
        nama_sel = st.selectbox("Pilih Nama Warga", sorted(df_warga['Nama'].tolist()))
        role_sel = df_warga.loc[df_warga['Nama'] == nama_sel, 'Role'].values[0]
        with st.form("f_kas"):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.number_input("Nominal Bayar (Rp)", min_value=0, step=5000)
                tp = st.selectbox("Tipe Alokasi", ["Paket Lengkap"] if role_sel == "Main Warga" else ["Hanya Kas", "Hanya Hadiah"])
            with c2:
                th = st.selectbox("Untuk Tahun", list(range(2022, 2031)), index=4)
                bl = st.selectbox("Mulai Bulan", bln_order)
            if st.form_submit_button("💰 SIMPAN PEMBAYARAN"):
                if nom > 0:
                    res = proses_bayar(nama_sel, nom, th, bl, tp, role_sel, df_masuk)
                    append_to_cloud("Pemasukan", res)
                    st.success(f"Berhasil simpan data {nama_sel}")
                    time.sleep(1); st.rerun()

elif menu == "🎭 Event & Iuran":
    st.subheader("🎭 Input Iuran Event")
    list_ev = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
    col1, col2 = st.columns(2)
    with col1:
        ev_p = st.selectbox("Pilih/Buat Event", ["-- Pilih --"] + list_ev + ["➕ Tambah Baru"])
        ev_f = st.text_input("Nama Event Baru") if ev_p == "➕ Tambah Baru" else ev_p
    with col2:
        warga_e = st.selectbox("Nama Penyumbang", sorted(df_warga['Nama'].tolist()))
    
    with st.form("f_ev"):
        nom_e = st.number_input("Nominal Iuran", min_value=0, step=5000)
        ket_e = st.text_input("Catatan Tambahan")
        if st.form_submit_button("🚀 SIMPAN IURAN"):
            if nom_e > 0 and ev_f != "-- Pilih --":
                new_ev = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Nama': warga_e, 'Nama Event': ev_f, 'Jumlah': nom_e, 'Keterangan': ket_e}])
                append_to_cloud("Event", new_ev)
                st.success("Data Event tersimpan!")
                time.sleep(1); st.rerun()

elif menu == "📤 Pengeluaran":
    st.subheader("📤 Catat Pengeluaran Dana")
    with st.form("f_out"):
        kat_o = st.radio("Ambil Dari Dana", ["Kas", "Hadiah", "Event"], horizontal=True)
        ev_label = ""
        if kat_o == "Event":
            ev_label = st.selectbox("Pilih Event Terkait", df_event['Nama Event'].unique() if not df_event.empty else ["Umum"])
        jml_o = st.number_input("Nominal Pengeluaran", min_value=0, step=1000)
        ket_o = st.text_input("Keterangan Barang/Jasa")
        if st.form_submit_button("🛑 SIMPAN PENGELUARAN"):
            if jml_o > 0 and ket_o:
                k_final = f"[{ev_label}] {ket_o}" if kat_o == "Event" else ket_o
                df_o = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Kategori': kat_o, 'Jumlah': jml_o, 'Keterangan': k_final}])
                append_to_cloud("Pengeluaran", df_o)
                st.success("Pengeluaran dicatat!")
                time.sleep(1); st.rerun()

elif menu == "👥 Kelola Warga":
    st.subheader("👥 Database Warga")
    t1, t2, t3 = st.tabs(["Tambah", "Edit", "Hapus"])
    with t1:
        with st.form("add_w"):
            nw, rl = st.text_input("Nama"), st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Simpan Warga"):
                rewrite_cloud("Warga", pd.concat([df_warga, pd.DataFrame([{'Nama': nw, 'Role': rl}])], ignore_index=True))
                st.rerun()
    with t3:
        nd = st.selectbox("Hapus Nama", df_warga['Nama'])
        if st.button("Hapus") and st.checkbox("Yakin?"):
            rewrite_cloud("Warga", df_warga[df_warga['Nama'] != nd])
            st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("📜 Log Transaksi Terakhir")
    tipe = st.selectbox("Kategori Log", ["Pemasukan", "Event", "Pengeluaran"])
    dt = load_data(tipe)
    st.dataframe(dt.sort_index(ascending=False).head(20), use_container_width=True)
