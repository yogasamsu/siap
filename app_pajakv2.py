import streamlit as st
import pandas as pd
import plotly.express as px
import os
import glob

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Sistem Intelijen Pajak", page_icon="💰", layout="wide")

# ==========================================
# 2. FITUR KEAMANAN (LOGIN) - FIXED
# ==========================================
def check_password():
    """Mengembalikan True jika user memasukkan password yang benar."""
    
    # Tentukan Password
    try:
        RAHASIA = st.secrets["password"]
    except:
        RAHASIA = "admin123" # Default untuk Local

    # Inisialisasi State
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # Fungsi Callback untuk Cek Password
    def password_entered():
        if st.session_state["password_input"] == RAHASIA:
            st.session_state.password_correct = True
            del st.session_state["password_input"]  # Hapus password dari memori
        else:
            st.session_state.password_correct = False

    # Tampilan Form Login (Jika belum login)
    if not st.session_state.password_correct:
        st.text_input(
            "🔒 Masukkan Password Sistem:", 
            type="password", 
            on_change=password_entered, 
            key="password_input"
        )
        
        # Tampilkan error jika password salah (tapi bukan saat pertama kali buka)
        if "password_input" in st.session_state and not st.session_state.password_correct:
             st.error("⛔ Password Salah!")
             
        return False
    
    return True

# Cek Password
if not check_password():
    st.stop()

# ==========================================
# 4. LOAD DATA (VERSI DIET MEMORI)
# ==========================================
@st.cache_data
def load_data():
    # --- A. LOAD RFM PROFILE ---
    path_rfm = 'hasil_rfm_individu_final.csv'
    df_rfm = None
    
    if os.path.exists(path_rfm):
        try:
            # Load RFM seperti biasa (ini filenya kecil, jadi aman)
            df_rfm = pd.read_csv(path_rfm)
            
            # Standarisasi Nama Kolom
            if 'NAMA_WP' not in df_rfm.columns: df_rfm['NAMA_WP'] = "WP-" + df_rfm.index.astype(str)
            df_rfm['NAMA_SEARCH'] = df_rfm['NAMA_WP'].fillna('').astype(str).str.upper()
            if 'ID_WP_INDIVIDUAL' not in df_rfm.columns: df_rfm['ID_WP_INDIVIDUAL'] = df_rfm.index
        except Exception as e:
            st.error(f"Gagal load RFM: {e}")
    
    # --- B. LOAD TRANSAKSI (OPTIMISASI RAM EKSTREM) ---
    df_transaksi = None
    
    chunk_files = glob.glob("data_chunks/data_part_*.csv")
    if not chunk_files:
        chunk_files = glob.glob("data_part_*.csv") 

    if chunk_files:
        try:
            chunk_files.sort()
            dfs = []
            
            # Kolom yang WAJIB saja. Buang yang lain untuk hemat RAM.
            # Kita TIDAK butuh Nama/Alamat di tabel transaksi karena sudah ada di RFM
            cols_to_keep = [
                'KD_PROPINSI', 'KD_DATI2', 'KD_KECAMATAN', 'KD_KELURAHAN', 
                'NM_WP_SPPT', 'ALAMAT_WP', # Kita butuh ini CUMA untuk bikin ID, nanti dibuang
                'THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'STATUS_PEMBAYARAN_SPPT'
            ]

            # Tipe data hemat memori
            dtypes = {
                'KD_PROPINSI': 'int8', 'KD_DATI2': 'int8', 
                'KD_KECAMATAN': 'int16', 'KD_KELURAHAN': 'int16',
                'THN_PAJAK_SPPT': 'int16', 'STATUS_PEMBAYARAN_SPPT': 'int8',
                'PBB_YG_HARUS_DIBAYAR_SPPT': 'float32'
            }

            for f in chunk_files:
                # 1. Baca pecahan
                chunk = pd.read_csv(f, usecols=lambda c: c in cols_to_keep, dtype=dtypes, low_memory=False)
                
                # 2. Langsung buat ID di pecahan kecil (lebih ringan)
                # (Kita pakai try-except untuk handle jika kolom nama tidak string)
                chunk['ID_WP_INDIVIDUAL'] = (
                    chunk['KD_PROPINSI'].astype(str).str.zfill(2) + '-' +
                    chunk['KD_DATI2'].astype(str).str.zfill(2) + '-' +
                    chunk['KD_KECAMATAN'].astype(str).str.zfill(3) + '-' +
                    chunk['KD_KELURAHAN'].astype(str).str.zfill(3) + '_' + 
                    chunk['NM_WP_SPPT'].astype(str).str.strip().str.upper() + '_' + 
                    chunk['ALAMAT_WP'].astype(str).str.strip().str.upper()
                )
                
                # 3. BUANG KOLOM SAMPAH SEGERA!
                # Setelah ID jadi, kita tidak butuh lagi kolom-kolom pembentuknya di memori
                chunk = chunk[['ID_WP_INDIVIDUAL', 'THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'STATUS_PEMBAYARAN_SPPT']]
                
                dfs.append(chunk)
            
            if dfs:
                # Gabung data yang sudah kurus
                df_transaksi = pd.concat(dfs, ignore_index=True)
                
        except Exception as e:
            st.warning(f"Gagal memproses data chunks: {e}")
    
    return df_rfm, df_transaksi
# ==========================================
# 4. NAVIGASI
# ==========================================
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

def go_to_detail(wp_id):
    st.session_state.selected_id = wp_id

def go_back():
    st.session_state.selected_id = None

# ==========================================
# 5. HALAMAN PENCARIAN
# ==========================================
def show_search_page(df_rfm): # <--- Perhatikan: Menerima parameter df_rfm
    st.title("🔍 Pencarian Wajib Pajak")
    
    if df_rfm is None:
        st.error("⚠️ Data Profil (RFM) tidak ditemukan. Pastikan file 'hasil_rfm_individu_final.csv' ada di GitHub.")
        st.stop()

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Cari Nama / ID / Alamat:", placeholder="Ketik nama...").upper()
    
    st.markdown("---")

    if query:
        hasil = df_rfm[
            df_rfm['NAMA_SEARCH'].str.contains(query, na=False) | 
            df_rfm['ID_WP_INDIVIDUAL'].astype(str).str.contains(query, na=False)
        ]
        
        if len(hasil) == 0:
            st.warning("Tidak ditemukan.")
        else:
            st.success(f"Ditemukan {len(hasil)} data.")
            for index, row in hasil.head(10).iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    c1.markdown(f"**{row.get('NAMA_WP','-')}**")
                    c1.caption(f"{row.get('ALAMAT_WP','-')}")
                    
                    segmen = str(row.get('Segment', '-'))
                    if "Berisiko" in segmen: c2.error(segmen)
                    elif "Champions" in segmen: c2.success(segmen)
                    else: c2.info(segmen)
                        
                    c3.metric("Total Bayar", f"Rp {row.get('Monetary',0):,.0f}")
                    
                    if c4.button("Detail ➡️", key=f"btn_{index}"):
                        go_to_detail(row['ID_WP_INDIVIDUAL'])
                    st.markdown("---")

# ==========================================
# 6. HALAMAN DETAIL
# ==========================================
def show_detail_page(df_rfm, df_trans): # <--- Menerima parameter
    wp_id = st.session_state.selected_id
    
    if df_rfm is None: return
    
    profil_data = df_rfm[df_rfm['ID_WP_INDIVIDUAL'] == wp_id]
    if profil_data.empty:
        st.error("Data tidak ditemukan.")
        st.button("Kembali", on_click=go_back)
        return

    profil = profil_data.iloc[0]
    
    st.button("⬅️ Kembali", on_click=go_back)
    st.title(f"👤 {profil.get('NAMA_WP','-')}")
    st.caption(f"ID: {wp_id}")
    st.info(f"📍 {profil.get('ALAMAT_WP','-')}")
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Segmen", profil.get('Segment','-'))
    c2.metric("Monetary", f"Rp {profil.get('Monetary',0):,.0f}")
    c3.metric("Frequency", f"{profil.get('Frequency',0)} Kali")
    c4.metric("Recency", f"{profil.get('Recency',0)} Hari")

    st.markdown("---")
    
    # Grafik
    if df_trans is not None:
        histori = df_trans[df_trans['ID_WP_INDIVIDUAL'] == wp_id].sort_values('THN_PAJAK_SPPT')
        
        if not histori.empty:
            histori['Status'] = histori['STATUS_PEMBAYARAN_SPPT'].map({1:'Lunas', 0:'Tunggakan'})
            fig = px.bar(histori, x='THN_PAJAK_SPPT', y='PBB_YG_HARUS_DIBAYAR_SPPT', color='Status',
                         color_discrete_map={'Lunas':'#2ecc71', 'Tunggakan':'#e74c3c'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabel
            view = histori[['THN_PAJAK_SPPT','PBB_YG_HARUS_DIBAYAR_SPPT','Status']]
            st.dataframe(view, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada data transaksi detail.")
    else:
        st.warning("Database transaksi belum tersedia (Folder data_chunks belum diupload).")

# ==========================================
# 7. MAIN ROUTING
# ==========================================
if st.session_state.selected_id is not None:
    show_detail_page(MAIN_DF_RFM, MAIN_DF_TRANSAKSI)
else:
    show_search_page(MAIN_DF_RFM)