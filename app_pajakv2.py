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
# 2. FITUR KEAMANAN (LOGIN)
# ==========================================
def check_password():
    """Mengembalikan True jika user memasukkan password yang benar."""
    try:
        RAHASIA = st.secrets["password"]
    except:
        RAHASIA = "admin123" # Default untuk Local

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Password:", type="password", on_change=lambda: None, key="password_input")
        if st.session_state.get("password_input") == RAHASIA:
            st.session_state["password_correct"] = True
            st.rerun()
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# 3. LOAD DATA (VERSI CHUNKS / PECAHAN)
# ==========================================
@st.cache_data
def load_data():
    # --- A. LOAD RFM PROFILE ---
    path_rfm = 'hasil_rfm_individu_final.csv'
    df_rfm = None
    
    if os.path.exists(path_rfm):
        try:
            df_rfm = pd.read_csv(path_rfm)
            # Standarisasi Nama Kolom
            if 'NAMA_WP' not in df_rfm.columns: df_rfm['NAMA_WP'] = "WP-" + df_rfm.index.astype(str)
            df_rfm['NAMA_SEARCH'] = df_rfm['NAMA_WP'].fillna('').astype(str).str.upper()
            if 'ID_WP_INDIVIDUAL' not in df_rfm.columns: df_rfm['ID_WP_INDIVIDUAL'] = df_rfm.index
        except Exception as e:
            st.error(f"Gagal load RFM: {e}")
    
    # --- B. LOAD TRANSAKSI (DARI CHUNKS) ---
    df_transaksi = None
    
    # Coba cari di folder 'data_chunks' atau di root
    chunk_files = glob.glob("data_chunks/data_part_*.csv")
    if not chunk_files:
        chunk_files = glob.glob("data_part_*.csv") # Coba cari di root jika folder tidak ada

    if chunk_files:
        try:
            dfs = []
            for f in chunk_files:
                dfs.append(pd.read_csv(f, parse_dates=['TGL_TERBIT_SPPT'], low_memory=False))
            
            if dfs:
                df_transaksi = pd.concat(dfs, ignore_index=True)
                # Bersihkan ID untuk Join
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
            st.warning(f"Gagal menggabungkan data chunks: {e}")
    
    return df_rfm, df_transaksi

# EKSEKUSI LOAD DATA (Di Global Scope)
# Variabel ini akan dilempar ke fungsi-fungsi di bawah
MAIN_DF_RFM, MAIN_DF_TRANSAKSI = load_data()

# --- DEBUGGING: CEK FILE DI SERVER ---
st.sidebar.warning("🛠️ Debug Mode: On")
current_path = os.getcwd()
st.sidebar.write(f"📂 Folder Saat Ini: `{current_path}`")

st.sidebar.write("📁 Isi Folder Root:")
st.sidebar.code(os.listdir(current_path))

if os.path.exists("data_chunks"):
    st.sidebar.success("✅ Folder 'data_chunks' DITEMUKAN!")
    st.sidebar.write("📄 Isi Folder 'data_chunks':")
    st.sidebar.code(os.listdir("data_chunks"))
else:
    st.sidebar.error("❌ Folder 'data_chunks' TIDAK DITEMUKAN di sini.")
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