import streamlit as st
import pandas as pd
import plotly.express as px
import os
import zipfile

# ==========================================
# 1. KONFIGURASI & SESSION STATE
# ==========================================
st.set_page_config(page_title="Sistem Intelijen Pajak", page_icon="💰", layout="wide")

# Inisialisasi state untuk navigasi halaman
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

# FUNGSI NAVIGASI (CALLBACK)
def go_to_detail(wp_id):
    st.session_state.selected_id = wp_id

def go_back():
    st.session_state.selected_id = None

# ==========================================
# 2. LOAD DATA (CACHE & ZIP HANDLING)
# ==========================================
@st.cache_data
def load_data():
    # --- 1. Data Profil RFM ---
    path_rfm = 'hasil_rfm_individu_final.csv'
    
    if not os.path.exists(path_rfm): 
        # Return None jika file tidak ada, nanti akan dihandle di UI
        return None, None
        
    df_rfm = pd.read_csv(path_rfm)
    
    # --- 2. Data Transaksi Historis (ZIP) ---
    path_transaksi_zip = 'sppt_ready.csv.zip'
    
    df_transaksi = None # Default None

    if os.path.exists(path_transaksi_zip): 
        try:
            with zipfile.ZipFile(path_transaksi_zip, 'r') as z:
                # Cari nama file CSV di dalam ZIP (abaikan folder __MACOSX)
                file_list = z.namelist()
                csv_files = [f for f in file_list if f.endswith('.csv') and not f.startswith('__MACOSX')]
                
                if csv_files:
                    target_file = csv_files[0]
                    # Baca CSV dari dalam ZIP
                    df_transaksi = pd.read_csv(z.open(target_file), parse_dates=['TGL_TERBIT_SPPT'], low_memory=False)
                    
                    # Bersihkan Data Transaksi
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
            st.error(f"Gagal membaca file Transaksi: {e}")

    # Bersihkan Nama di RFM untuk pencarian
    if df_rfm is not None:
        df_rfm['NAMA_SEARCH'] = df_rfm['NAMA_WP'].fillna('').astype(str).str.upper()
        if 'ID_WP_INDIVIDUAL' not in df_rfm.columns:
            df_rfm['ID_WP_INDIVIDUAL'] = df_rfm.index

    return df_rfm, df_transaksi

# --- INI BARIS PENTING YANG TADI HILANG ---
# Kita harus menjalankan fungsi load_data() agar variabel df_rfm tersedia
df_rfm, df_transaksi = load_data()
# ------------------------------------------

# ==========================================
# 3. HALAMAN PENCARIAN (HALAMAN UTAMA)
# ==========================================
def show_search_page():
    st.title("🔍 Pencarian Wajib Pajak")
    
    if df_rfm is None:
        st.error("File Data (CSV) tidak ditemukan di Server. Pastikan upload berhasil.")
        st.stop() # Berhenti jika data tidak ada

    # Input Pencarian
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Masukkan Nama / NOP / Alamat:", placeholder="Contoh: YOGA PRATAMA").upper()
    
    st.markdown("---")

    if query:
        # Filter Data RFM
        hasil = df_rfm[
            df_rfm['NAMA_SEARCH'].str.contains(query, na=False) | 
            df_rfm['ID_WP_INDIVIDUAL'].astype(str).str.contains(query, na=False)
        ]
        
        if len(hasil) == 0:
            st.warning("Tidak ditemukan data.")
        else:
            st.success(f"Ditemukan {len(hasil)} Wajib Pajak.")
            
            # Tampilkan max 20 hasil biar ga berat
            for index, row in hasil.head(20).iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    c1.markdown(f"**{row['NAMA_WP']}**")
                    c1.caption(f"{row['ALAMAT_WP']}")
                    
                    # Badge Status
                    segmen = str(row['Segment'])
                    if "Berisiko" in segmen:
                        c2.markdown(f":red[**{segmen}**]")
                    elif "Champions" in segmen:
                        c2.markdown(f":green[**{segmen}**]")
                    else:
                        c2.markdown(f"**{segmen}**")
                        
                    c3.metric("Total Bayar", f"Rp {row['Monetary']:,.0f}")
                    
                    # Tombol Detail
                    if c4.button("Lihat Detail ➡️", key=f"btn_{row['ID_WP_INDIVIDUAL']}"):
                        go_to_detail(row['ID_WP_INDIVIDUAL'])
                    
                    st.markdown("---")

# ==========================================
# 4. HALAMAN DETAIL WP (HALAMAN KEDUA)
# ==========================================
def show_detail_page():
    wp_id = st.session_state.selected_id
    
    # Ambil Data Profil
    profil = df_rfm[df_rfm['ID_WP_INDIVIDUAL'] == wp_id].iloc[0]
    
    st.button("⬅️ Kembali ke Pencarian", on_click=go_back)
    
    # --- HEADER ---
    st.title(f"👤 {profil['NAMA_WP']}")
    st.caption(f"ID: {wp_id}")
    st.info(f"📍 {profil['ALAMAT_WP']}")
    
    # --- STATUS RFM ---
    st.subheader("📊 Status & Kesehatan Pajak")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Segmen", profil['Segment'])
    c2.metric("Total Kontribusi", f"Rp {profil['Monetary']:,.0f}")
    c3.metric("Frekuensi Bayar", f"{profil['Frequency']} Kali")
    c4.metric("Terakhir Bayar", f"{profil['Recency']} Hari Lalu")

    if "Berisiko" in str(profil['Segment']):
        st.error("⚠️ **WARNING:** WP ini masuk kategori Berisiko Tinggi.")
    elif "Champions" in str(profil['Segment']):
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
                
                # --- DETEKSI TUNGGAKAN vs DATA HILANG ---
                tunggakan_tercatat = histori[histori['STATUS_PEMBAYARAN_SPPT'] == 0]
                
                # 1. Cek Tunggakan Resmi (Status = 0)
                if not tunggakan_tercatat.empty:
                    total_hutang = tunggakan_tercatat['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()
                    st.error(f"💸 **Tunggakan Tercatat: Rp {total_hutang:,.0f}**")
                
                # 2. Cek Data Hilang (Stop Bayar)
                max_tahun_global = df_transaksi['THN_PAJAK_SPPT'].max()
                max_tahun_wp = histori['THN_PAJAK_SPPT'].max()
                gap_tahun = max_tahun_global - max_tahun_wp
                
                if gap_tahun > 0:
                    st.warning(f"""
                    ⚠️ **PERHATIAN DATA:**
                    Data SPPT WP ini berhenti di tahun **{max_tahun_wp}**.
                    Ada kemungkinan **{gap_tahun} tahun terakhir** (sampai {max_tahun_global}) belum terbit SPPT atau datanya belum masuk sistem.
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
        st.warning("Database Transaksi (SPPT) tidak tersedia.")

# ==========================================
# 5. MAIN APP LOGIC
# ==========================================
if st.session_state.selected_id is not None:
    show_detail_page()
else:
    show_search_page()