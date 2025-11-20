import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob  # Library untuk mencari daftar file

# ==========================================
# 1. KONFIGURASI HALAMAN (WAJIB PALING ATAS)
# ==========================================
st.set_page_config(page_title="Sistem Intelijen Pajak", page_icon="💰", layout="wide")

# ==========================================
# 2. FITUR KEAMANAN (LOGIN PASSWORD)
# ==========================================
def check_password():
    """Mengembalikan True jika user memasukkan password yang benar."""
    
    # --- KONFIGURASI PASSWORD ---
    # Ganti "admin123" dengan password yang Anda inginkan
    RAHASIA = st.secrets["password"] if "password" in st.secrets else "admin123"

    def password_entered():
        if st.session_state["password"] == RAHASIA:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "🔒 Masukkan Password Sistem:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "🔒 Masukkan Password Sistem:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("⛔ Password Salah!")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# 3. STATE MANAGEMENT & NAVIGASI
# ==========================================
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

def go_to_detail(wp_id):
    st.session_state.selected_id = wp_id

def go_back():
    st.session_state.selected_id = None

# ==========================================
# 4. LOAD DATA (BACA DARI CHUNKS/PECAHAN)
# ==========================================
@st.cache_data
def load_data():
    # --- A. Data Profil RFM ---
    path_rfm = 'hasil_rfm_individu_final.csv'
    df_rfm = None 
    
    if os.path.exists(path_rfm): 
        try:
            df_rfm = pd.read_csv(path_rfm)
        except Exception as e:
            st.error(f"Gagal membaca file RFM: {e}")
    
    # --- B. Data Transaksi Historis (BACA BANYAK FILE) ---
    df_transaksi = None 
    
    # 1. Cari file pecahan di folder 'data_chunks'
    # (Sesuaikan path ini jika file pecahan Anda ada di root folder)
    chunk_folder = 'data_chunks' 
    if os.path.exists(chunk_folder):
        files = glob.glob(os.path.join(chunk_folder, "data_part_*.csv"))
    else:
        # Coba cari di folder utama jika tidak ada folder khusus
        files = glob.glob("data_part_*.csv")
        
    if files:
        try:
            files.sort() # Urutkan biar part_01, part_02 dst rapi
            
            # Baca dan gabung semua file
            dfs = []
            for f in files:
                temp = pd.read_csv(f, parse_dates=['TGL_TERBIT_SPPT'], low_memory=False)
                dfs.append(temp)
            
            if dfs:
                df_transaksi = pd.concat(dfs, ignore_index=True)
                
                # Bersihkan Data Transaksi (Standarisasi ID)
                # (Wajib dilakukan karena data mentah belum punya ID gabungan)
                df_transaksi['NM_WP_CLEAN'] = df_transaksi['NM_WP_SPPT'].astype(str).str.strip().str.upper()
                df_transaksi['ALAMAT_CLEAN'] = df_transaksi['ALAMAT_WP'].astype(str).str.strip().str.upper()
                df_transaksi['ID_WP_INDIVIDUAL'] = (
                    df_transaksi['KD_PROPINSI'].astype(str).str.zfill(2) + '-' +
                    df_transaksi['KD_DATI2'].astype(str).str.zfill(2) + '-' +
                    df_transaksi['KD_KECAMATAN'].astype(str).str.zfill(3) + '-' +
                    df_transaksi['KD_KELURAHAN'].astype(str).str.zfill(3) + '_' + 
                    df_transaksi['NM_WP_CLEAN'] + '_' + 
                    df_transaksi['ALAMAT_CLEAN']
                )
        except Exception as e:
            st.error(f"Gagal menggabungkan data transaksi: {e}")
    else:
        st.warning("Tidak ditemukan file pecahan data transaksi (data_part_*.csv). Grafik historis tidak akan muncul.")

    # Bersihkan Nama di RFM untuk pencarian
    if df_rfm is not None:
        if 'NAMA_WP' not in df_rfm.columns: df_rfm['NAMA_WP'] = "WP-" + df_rfm.index.astype(str)
        df_rfm['NAMA_SEARCH'] = df_rfm['NAMA_WP'].fillna('').astype(str).str.upper()
        if 'ID_WP_INDIVIDUAL' not in df_rfm.columns: df_rfm['ID_WP_INDIVIDUAL'] = df_rfm.index

    return df_rfm, df_transaksi

# EKSEKUSI LOAD DATA
df_rfm, df_transaksi = load_data()

# ==========================================
# 5. HALAMAN PENCARIAN (UTAMA)
# ==========================================
def show_search_page():
    st.title("🔍 Pencarian Wajib Pajak")
    
    if df_rfm is None:
        st.error("⚠️ File Data Profil (hasil_rfm_individu_final.csv) tidak ditemukan.")
        st.stop()

    # Input Pencarian
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Masukkan Nama / NOP / Alamat:", placeholder="Contoh: YOGA PRATAMA").upper()
    
    st.markdown("---")

    if query:
        # Filter Data
        hasil = df_rfm[
            df_rfm['NAMA_SEARCH'].str.contains(query, na=False) | 
            df_rfm['ID_WP_INDIVIDUAL'].astype(str).str.contains(query, na=False)
        ]
        
        if len(hasil) == 0:
            st.warning("Tidak ditemukan data.")
        else:
            st.success(f"Ditemukan {len(hasil)} Wajib Pajak.")
            
            # Tampilkan hasil (Maksimal 20 agar ringan)
            for index, row in hasil.head(20).iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    c1.markdown(f"**{row['NAMA_WP']}**")
                    
                    alamat = row.get('ALAMAT_WP', '-')
                    c1.caption(f"{alamat}")
                    
                    # Badge Status
                    segmen = str(row.get('Segment', 'Unknown'))
                    if "Berisiko" in segmen:
                        c2.markdown(f":red[**{segmen}**]")
                    elif "Champions" in segmen:
                        c2.markdown(f":green[**{segmen}**]")
                    else:
                        c2.markdown(f"**{segmen}**")
                        
                    monetary = row.get('Monetary', 0)
                    c3.metric("Total Bayar", f"Rp {monetary:,.0f}")
                    
                    # Tombol Detail
                    if c4.button("Lihat Detail ➡️", key=f"btn_{row['ID_WP_INDIVIDUAL']}"):
                        go_to_detail(row['ID_WP_INDIVIDUAL'])
                    
                    st.markdown("---")

# ==========================================
# 6. HALAMAN DETAIL (DRILLED DOWN)
# ==========================================
def show_detail_page():
    wp_id = st.session_state.selected_id
    
    if df_rfm is None:
        st.error("Data tidak tersedia.")
        st.button("⬅️ Kembali", on_click=go_back)
        return

    profil_data = df_rfm[df_rfm['ID_WP_INDIVIDUAL'] == wp_id]
    
    if profil_data.empty:
        st.error("Data WP tidak ditemukan.")
        st.button("⬅️ Kembali", on_click=go_back)
        return

    profil = profil_data.iloc[0]
    
    st.button("⬅️ Kembali ke Pencarian", on_click=go_back)
    
    # --- HEADER ---
    nama = profil.get('NAMA_WP', 'Tanpa Nama')
    alamat = profil.get('ALAMAT_WP', '-')
    st.title(f"👤 {nama}")
    st.caption(f"ID: {wp_id}")
    st.info(f"📍 {alamat}")
    
    # --- STATUS RFM ---
    st.subheader("📊 Status & Kesehatan Pajak")
    c1, c2, c3, c4 = st.columns(4)
    
    segmen = str(profil.get('Segment', '-'))
    monetary = profil.get('Monetary', 0)
    freq = profil.get('Frequency', 0)
    recency = profil.get('Recency', 0)

    c1.metric("Segmen", segmen)
    c2.metric("Total Kontribusi", f"Rp {monetary:,.0f}")
    c3.metric("Frekuensi Bayar", f"{freq} Kali")
    c4.metric("Terakhir Bayar", f"{recency} Hari Lalu")

    if "Berisiko" in segmen:
        st.error("⚠️ **WARNING:** WP ini masuk kategori Berisiko Tinggi.")
    elif "Champions" in segmen:
        st.success("✅ **CHAMPION:** WP ini sangat patuh.")

    st.markdown("---")
    
    # --- DATA HISTORIS ---
    if df_transaksi is not None:
        histori = df_transaksi[df_transaksi['ID_WP_INDIVIDUAL'] == wp_id].sort_values('THN_PAJAK_SPPT')
        
        if not histori.empty:
            c_chart, c_data = st.columns([2, 1])
            
            with c_chart:
                st.subheader("📈 Grafik Tren Pembayaran")
                
                histori['Status'] = histori['STATUS_PEMBAYARAN_SPPT'].map({1: 'Lunas', 0: 'Tunggakan'})
                
                fig = px.bar(
                    histori, 
                    x='THN_PAJAK_SPPT', 
                    y='PBB_YG_HARUS_DIBAYAR_SPPT',
                    color='Status',
                    color_discrete_map={'Lunas': '#2ecc71', 'Tunggakan': '#e74c3c'},
                    title="Riwayat Tagihan PBB"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # --- LOGIKA DETEKSI RISIKO ---
                tunggakan_tercatat = histori[histori['STATUS_PEMBAYARAN_SPPT'] == 0]
                if not tunggakan_tercatat.empty:
                    total_hutang = tunggakan_tercatat['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()
                    st.error(f"💸 **Tunggakan Tercatat: Rp {total_hutang:,.0f}**")
                
                max_tahun_global = df_transaksi['THN_PAJAK_SPPT'].max()
                max_tahun_wp = histori['THN_PAJAK_SPPT'].max()
                gap_tahun = max_tahun_global - max_tahun_wp
                
                if gap_tahun > 0:
                    st.warning(f"""
                    ⚠️ **PERHATIAN DATA:**
                    Data SPPT berhenti di tahun **{max_tahun_wp}**.
                    Ada kemungkinan **{gap_tahun} tahun terakhir** belum terbit SPPT/data belum update.
                    """)
                
                if tunggakan_tercatat.empty and gap_tahun == 0:
                    st.success("🎉 Bersih! Tidak ada tunggakan tercatat.")

            with c_data:
                st.subheader("🗂️ Tabel Historis")
                view = histori[['THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'Status']].copy()
                view['PBB_YG_HARUS_DIBAYAR_SPPT'] = view['PBB_YG_HARUS_DIBAYAR_SPPT'].apply(lambda x: f"{x:,.0f}")
                st.dataframe(view, hide_index=True, use_container_width=True)
        else:
            st.info("Belum ada data transaksi historis yang ditemukan untuk ID ini.")
    else:
        st.warning("Database Transaksi (SPPT) tidak tersedia (File Chunks tidak ditemukan).")

# ==========================================
# 7. MAIN APP LOGIC (ROUTING)
# ==========================================
if st.session_state.selected_id is not None:
    show_detail_page()
else:
    show_search_page()