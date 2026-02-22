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

# LOAD SEMUA DATA
df_masuk = load_data("Pemasukan")
df_keluar = load_data("Pengeluaran")
df_warga = load_data("Warga")
df_event = load_data("Event")

# --- 5. SIDEBAR ---
st.sidebar.markdown(f"### 👤 {st.session_state['role'].upper()}")
if st.sidebar.button("🔄 Refresh Data"): clear_cache(); st.rerun()
if st.sidebar.button("🚪 Logout"): st.session_state.clear(); st.rerun()

list_menu = ["📊 Laporan", "📥 Kas Bulanan", "🎭 Event & Iuran", "📤 Pengeluaran", "👥 Kelola Warga", "📜 Log"] if st.session_state['role'] == "admin" else ["📊 Laporan", "📜 Log"]
menu = st.sidebar.radio("Navigasi", list_menu)

# --- 6. DASHBOARD METRIK (KOREKSI ERROR VARIABEL) ---
in_k, in_h = df_masuk['Kas'].sum(), df_masuk['Hadiah'].sum()
out_k = df_keluar[df_keluar['Kategori'] == 'Kas']['Jumlah'].sum()
out_h = df_keluar[df_keluar['Kategori'] == 'Hadiah']['Jumlah'].sum()

# Hitung Saldo Bersih Event (Masuk - Keluar)
in_ev_total = df_event['Jumlah'].sum() if not df_event.empty else 0
out_ev_total = df_keluar[df_keluar['Kategori'] == 'Event']['Jumlah'].sum() if not df_keluar.empty else 0
saldo_event_bersih = in_ev_total - out_ev_total

st.markdown(f"## 🏦 KAS & EVENT AR-ROYHAAN 3")
m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 SALDO KAS", f"Rp {in_k - out_k:,.0f}")
m2.metric("🎁 SALDO HADIAH", f"Rp {in_h - out_h:,.0f}")
m3.metric("🎭 SALDO EVENT", f"Rp {saldo_event_bersih:,.0f}")
# Koreksi variabel total_ev_masuk jadi in_ev_total
m4.metric("🏦 TOTAL TUNAI", f"Rp {(in_k+in_h+in_ev_total)-(out_k+out_h+out_ev_total):,.0f}")
st.divider()

# --- 7. MENU LOGIC ---

f menu == "📊 Laporan":
    st.subheader("📋 Laporan Keuangan Terpisah")
    
    tab_kas, tab_event, tab_keluar = st.tabs(["💰 Kas Bulanan", "🎭 Saldo Per Event", "📤 Pengeluaran"])
    
    with tab_kas:
        st.write("### 📅 Rekap Kas Warga (Bulanan)")
        thn_lap = st.selectbox("Pilih Tahun", list(range(2022, 2031)), index=4)
        df_yr_in = df_masuk[df_masuk['Tahun'] == thn_lap]
        
        if not df_yr_in.empty:
            # Tampilan Pivot: Baris = Nama, Kolom = Bulan, Isi = Total Bayar
            rk = df_yr_in.pivot_table(index='Nama', columns='Bulan', values='Total', aggfunc='sum').fillna(0)
            
            # Urutan bulan biar gak acak
            bln_order = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            cols = [b for b in bln_order if b in rk.columns]
            
            # Tampilkan Tabel dengan Highlight Hijau jika sudah bayar Rp 50.000 (Paket Lengkap)
            st.dataframe(
                rk[cols].style.highlight_between(left=50000, color='#d4edda').format("{:,.0f}"), 
                use_container_width=True
            )
        else:
            st.info(f"Data kas tahun {thn_lap} masih kosong.")

    with tab_event:
        st.write("### 🎭 Saldo Berdasarkan Jenis Event")
        if not df_event.empty:
            list_ev_laporan = df_event['Nama Event'].unique().tolist()
            ev_pilihan = st.selectbox("Pilih Event untuk Detail", list_ev_laporan)
            
            # 1. Hitung Pemasukan Event
            df_ev_in = df_event[df_event['Nama Event'] == ev_pilihan]
            total_in = df_ev_in['Jumlah'].sum()
            
            # 2. Hitung Pengeluaran Event (Mencari teks Event di keterangan pengeluaran)
            df_ev_out = df_keluar[(df_keluar['Kategori'] == 'Event') & (df_keluar['Keterangan'].str.contains(ev_pilihan, na=False))]
            total_out = df_ev_out['Jumlah'].sum()
            
            # Tampilan Metrik Event
            ce1, ce2, ce3 = st.columns(3)
            ce1.metric(f"Total Masuk {ev_pilihan}", f"Rp {total_in:,.0f}")
            ce2.metric(f"Total Keluar {ev_pilihan}", f"Rp {total_out:,.0f}")
            ce3.metric(f"Saldo Bersih", f"Rp {total_in - total_out:,.0f}")
            
            st.divider()
            d1, d2 = st.columns(2)
            with d1:
                st.write("📋 Daftar Pembayar:")
                st.dataframe(df_ev_in[['Tanggal', 'Nama', 'Jumlah']].sort_values('Tanggal', ascending=False), use_container_width=True)
            with d2:
                st.write("💸 Riwayat Belanja:")
                st.dataframe(df_ev_out[['Tanggal', 'Jumlah', 'Keterangan']], use_container_width=True)
        else:
            st.info("Belum ada data iuran event.")

    with tab_keluar:
        st.write("### 📤 Laporan Pengeluaran")
        
        # Ringkasan Pengeluaran
        ok, oh, oe = st.columns(3)
        ok.metric("Duit Kas Keluar", f"Rp {out_k:,.0f}")
        oh.metric("Duit Hadiah Keluar", f"Rp {out_h:,.0f}")
        oe.metric("Duit Event Keluar", f"Rp {out_ev_total:,.0f}")
        
        st.divider()
        kat_filter = st.multiselect("Filter Kategori Pengeluaran:", ["Kas", "Hadiah", "Event"], default=["Kas", "Hadiah", "Event"])
        
        df_out_filtered = df_keluar[df_keluar['Kategori'].isin(kat_filter)]
        if not df_out_filtered.empty:
            st.dataframe(
                df_out_filtered[['Tanggal', 'Kategori', 'Jumlah', 'Keterangan']].sort_values('Tanggal', ascending=False), 
                use_container_width=True
            )
        else:
            st.info("Pilih kategori atau data pengeluaran kosong.")
elif menu == "🎭 Event & Iuran":
    st.subheader("🎭 Input Iuran Event / Kegiatan")
    if not df_warga.empty:
        list_ev = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
        col_a, col_b = st.columns(2)
        with col_a:
            ev_pilih = st.selectbox("Pilih Event", ["-- Pilih --"] + list_ev + ["➕ Tambah Event Baru"])
            ev_final = st.text_input("Nama Event Baru") if ev_pilih == "➕ Tambah Event Baru" else ev_pilih
        with col_b:
            warga_ev = st.selectbox("Pilih Warga", sorted(df_warga['Nama'].tolist()), key="ev_w")
        
        with st.form("f_ev"):
            c1, c2 = st.columns(2)
            with c1: nom_ev = st.number_input("Nominal Iuran", min_value=0, step=5000)
            with c2: ket_ev = st.text_input("Keterangan")
            if st.form_submit_button("Simpan Iuran Event"):
                if nom_ev > 0 and ev_final != "-- Pilih --":
                    data_ev = pd.DataFrame([{'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Nama': warga_ev, 'Nama Event': ev_final, 'Jumlah': nom_ev, 'Keterangan': ket_ev}])
                    append_to_cloud("Event", data_ev)
                    st.success(f"✅ Iuran {ev_final} Berhasil!")
                    time.sleep(1.5); st.rerun()

elif menu == "📤 Pengeluaran":
    st.subheader("📤 Catat Pengeluaran")
    with st.form("f_out", clear_on_submit=True):
        # Tambahkan "Event" di pilihan sumber dana
        kat = st.radio("Sumber Dana", ["Kas", "Hadiah", "Event"], horizontal=True)
        
        # Kalau pilih Event, munculin pilihan Event-nya yang mana
        nama_ev_out = ""
        if kat == "Event":
            list_ev_ada = df_event['Nama Event'].unique().tolist() if not df_event.empty else []
            nama_ev_out = st.selectbox("Pilih Dana Event Mana?", list_ev_ada)
        
        jml = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
        ket = st.text_input("Keterangan / Keperluan")
        
        if st.form_submit_button("Simpan Pengeluaran"):
            if jml > 0 and ket:
                # Jika kategori Event, simpan keterangan tambahan
                ket_final = f"[{nama_ev_out}] {ket}" if kat == "Event" else ket
                
                new_out = pd.DataFrame([{
                    'Tanggal': datetime.now().strftime("%d/%m/%Y %H:%M"),
                    'Kategori': kat,
                    'Jumlah': jml,
                    'Keterangan': ket_final
                }])
                append_to_cloud("Pengeluaran", new_out)
                st.success(f"✅ Pengeluaran {kat} Rp {jml:,.0f} Berhasil Dicatat!")
                time.sleep(1.5); st.rerun()
            else:
                st.error("Lengkapi jumlah dan keterangan!")

elif menu == "👥 Kelola Warga":
    st.subheader("👥 Database Anggota")
    t1, t2, t3 = st.tabs(["➕ Tambah", "✏️ Edit", "🗑️ Hapus"])
    with t1:
        with st.form("f_add"):
            nw, rl = st.text_input("Nama"), st.selectbox("Role", ["Main Warga", "Warga Support"])
            if st.form_submit_button("Simpan"):
                rewrite_cloud("Warga", pd.concat([df_warga, pd.DataFrame([{'Nama': nw, 'Role': rl}])], ignore_index=True))
                st.rerun()
    with t2:
        if not df_warga.empty:
            n_lama = st.selectbox("Pilih Nama", sorted(df_warga['Nama'].tolist()))
            with st.form("f_edit"):
                n_baru = st.text_input("Nama Baru", value=n_lama)
                r_baru = st.selectbox("Role", ["Main Warga", "Warga Support"])
                if st.form_submit_button("Update"):
                    df_warga.loc[df_warga['Nama'] == n_lama, ['Nama', 'Role']] = [n_baru, r_baru]
                    rewrite_cloud("Warga", df_warga)
                    if not df_masuk.empty:
                        df_masuk.loc[df_masuk['Nama'] == n_lama, 'Nama'] = n_baru
                        rewrite_cloud("Pemasukan", df_masuk)
                    st.rerun()
    with t3:
        n_del = st.selectbox("Hapus Nama", sorted(df_warga['Nama'].tolist()))
        if st.button("Hapus Permanen") and st.checkbox("Yakin?"):
            rewrite_cloud("Warga", df_warga[df_warga['Nama'] != n_del])
            st.rerun()
    st.table(df_warga)

elif menu == "📜 Log":
    st.subheader("📜 Log Transaksi Terakhir")
    tipe_log = st.selectbox("Pilih Jenis Log", ["Kas Bulanan", "Iuran Event", "Pengeluaran"])
    
    if tipe_log == "Kas Bulanan":
        df_target, s_name = df_masuk, "Pemasukan"
    elif tipe_log == "Iuran Event":
        df_target, s_name = df_event, "Event"
    else:
        df_target, s_name = df_keluar, "Pengeluaran"
        
    if not df_target.empty:
        df_show = df_target.sort_index(ascending=False).head(20)
        st.dataframe(df_show, use_container_width=True)
        
        # FITUR PRO: Hapus baris terakhir jika salah input
        if st.button(f"🗑️ Hapus Transaksi Teratas di {tipe_log}"):
            if st.checkbox("Saya sadar ini akan menghapus data di Google Sheets"):
                df_final = df_target.drop(df_target.index[-1])
                rewrite_cloud(s_name, df_final)
                st.success("Data berhasil dihapus!")
                time.sleep(1.5); st.rerun()
    else: st.info("Belum ada data.")
