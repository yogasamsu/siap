import streamlit as st
import pandas as pd
import plotly.express as px
import os

import streamlit as st

# --- FITUR LOGIN SEDERHANA ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Hapus password dari session
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("Password salah!")
        return False
    else:
        # Password correct.
        return True

if check_password():
    # ... TARUH SEMUA KODE APLIKASI ANDA DI BAWAH SINI (INDENTED/MENJOROK KE KANAN) ...
    # import libraries lain dst...
    pass
# ==========================================
# 1. KONFIGURASI & SESSION STATE
# ==========================================
st.set_page_config(page_title="Sistem Intelijen Pajak", page_icon="💰", layout="wide")

# Inisialisasi state untuk navigasi halaman
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

# FUNGSI CALLBACK (Hanya ubah state, jangan rerun manual)
def go_to_detail(wp_id):
    st.session_state.selected_id = wp_id

def go_back():
    st.session_state.selected_id = None

# ==========================================
# 2. LOAD DATA (PROFIL & TRANSAKSI)
# ==========================================
# ==========================================
# UPDATE BAGIAN LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    # 1. Data Profil RFM
    path_rfm = 'hasil_rfm_individu_final.csv'
    if not os.path.exists(path_rfm): return None, None
    df_rfm = pd.read_csv(path_rfm)
    
    # 2. Data Transaksi Historis (BACA DARI ZIP)
    # Kita ubah targetnya ke file ZIP
    path_transaksi_zip = 'sppt_ready.csv.zip' 
    
    if not os.path.exists(path_transaksi_zip): 
        st.error("File 'sppt_ready.csv.zip' tidak ditemukan!")
        return df_rfm, None
        
    # Tambahkan parameter compression='zip'
    df_transaksi = pd.read_csv(path_transaksi_zip, compression='zip', parse_dates=['TGL_TERBIT_SPPT'], low_memory=False)
    
    # ... (Kode pembersihan nama/alamat di bawahnya TETAP SAMA, tidak perlu diubah) ...
    df_transaksi['NM_WP_CLEAN'] = df_transaksi['NM_WP_SPPT'].astype(str).str.strip().str.upper()
    # dst...
    
    return df_rfm, df_transaksi
        
    df_transaksi = pd.read_csv(path_transaksi, parse_dates=['TGL_TERBIT_SPPT'], low_memory=False)
    
    # Pastikan ID WP Konsisten
    # (Kita recreate ID di df_transaksi agar sama persis dengan RFM)
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
    
    return df_rfm, df_transaksi

df_rfm, df_transaksi = load_data()

# ==========================================
# 3. HALAMAN PENCARIAN (HALAMAN UTAMA)
# ==========================================
def show_search_page():
    st.title("🔍 Pencarian Wajib Pajak")
    
    # Input Pencarian
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Masukkan Nama / NOP / Alamat:", placeholder="Contoh: YOGA PRATAMA").upper()
    
    st.markdown("---")

    if query and df_rfm is not None:
        # Filter Data RFM
        hasil = df_rfm[
            df_rfm['NAMA_WP'].astype(str).str.contains(query, na=False) | 
            df_rfm['ID_WP_INDIVIDUAL'].astype(str).str.contains(query, na=False)
        ]
        
        if len(hasil) == 0:
            st.warning("Tidak ditemukan data.")
        else:
            st.success(f"Ditemukan {len(hasil)} Wajib Pajak.")
            
            # Tampilkan sebagai Cards / List yang bisa diklik
            for index, row in hasil.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    c1.markdown(f"**{row['NAMA_WP']}**")
                    c1.caption(f"{row['ALAMAT_WP']}")
                    
                    # Badge Status
                    segmen = row['Segment']
                    if "Berisiko" in segmen:
                        c2.markdown(f":red[**{segmen}**]")
                    elif "Champions" in segmen:
                        c2.markdown(f":green[**{segmen}**]")
                    else:
                        c2.markdown(f"**{segmen}**")
                        
                    c3.metric("Total Bayar", f"Rp {row['Monetary']:,.0f}")
                    
                    # Tombol Detail
                    if c4.button("Lihat Detail ➡️", key=row['ID_WP_INDIVIDUAL']):
                        go_to_detail(row['ID_WP_INDIVIDUAL'])
                    
                    st.markdown("---")

# ==========================================
# GANTI FUNGSI show_detail_page() DENGAN INI
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

    if "Berisiko" in profil['Segment']:
        st.error("⚠️ **WARNING:** WP ini masuk kategori Berisiko Tinggi.")
    elif "Champions" in profil['Segment']:
        st.success("✅ **CHAMPION:** WP ini sangat patuh.")

    st.markdown("---")
    
    # --- DATA HISTORIS ---
    if df_transaksi is not None:
        histori = df_transaksi[df_transaksi['ID_WP_INDIVIDUAL'] == wp_id].sort_values('THN_PAJAK_SPPT')
        
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
            
            # --- LOGIKA BARU: DETEKSI TUNGGAKAN vs DATA HILANG ---
            tunggakan_tercatat = histori[histori['STATUS_PEMBAYARAN_SPPT'] == 0]
            
            # 1. Cek Tunggakan Resmi (Status = 0)
            if not tunggakan_tercatat.empty:
                total_hutang = tunggakan_tercatat['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()
                st.error(f"💸 **Tunggakan Tercatat: Rp {total_hutang:,.0f}**")
            
            # 2. Cek Data Hilang (Stop Bayar)
            # Cari tahun maksimal di seluruh database (misal 2023)
            max_tahun_global = df_transaksi['THN_PAJAK_SPPT'].max()
            # Cari tahun terakhir WP ini ada datanya (misal 2020)
            if not histori.empty:
                max_tahun_wp = histori['THN_PAJAK_SPPT'].max()
                
                # Jika WP berhenti muncul datanya lebih dari 1 tahun
                gap_tahun = max_tahun_global - max_tahun_wp
                if gap_tahun > 0:
                    st.warning(f"""
                    ⚠️ **PERHATIAN DATA:**
                    Data SPPT WP ini berhenti di tahun **{max_tahun_wp}**.
                    Ada kemungkinan **{gap_tahun} tahun terakhir** (sampai {max_tahun_global}) belum terbit SPPT atau datanya belum masuk sistem.
                    
                    **Indikasi:** WP Berpotensi Non-Aktif / Data Belum Update.
                    """)
            
            if tunggakan_tercatat.empty and (histori.empty or max_tahun_wp == max_tahun_global):
                st.success("🎉 Bersih! Tidak ada tunggakan tercatat.")

        with c_data:
            st.subheader("🗂️ Tabel Historis")
            view = histori[['THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'Status']].copy()
            view['PBB_YG_HARUS_DIBAYAR_SPPT'] = view['PBB_YG_HARUS_DIBAYAR_SPPT'].apply(lambda x: f"{x:,.0f}")
            st.dataframe(view, hide_index=True, use_container_width=True)

# ==========================================
# 5. MAIN APP LOGIC
# ==========================================
if st.session_state.selected_id is not None:
    show_detail_page()
else:
    show_search_page()