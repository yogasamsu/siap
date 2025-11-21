import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
        st.session_state.password_correct = False

    def password_entered():
        if st.session_state["password_input"] == RAHASIA:
            st.session_state.password_correct = True
            del st.session_state["password_input"]
        else:
            st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.text_input("🔒 Password:", type="password", on_change=password_entered, key="password_input")
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
    
    # --- B. LOAD TRANSAKSI (DARI FOLDER CHUNKS) ---
    df_transaksi = None
    
    chunk_files = glob.glob("data_chunks/data_part_*.csv")
    if not chunk_files:
        chunk_files = glob.glob("data_part_*.csv") 

    if chunk_files:
        try:
            chunk_files.sort()
            dfs = []
            
            # OPTIMASI MEMORI: Hanya load kolom penting
            cols_keep = ['THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'STATUS_PEMBAYARAN_SPPT', 
                         'KD_PROPINSI', 'KD_DATI2', 'KD_KECAMATAN', 'KD_KELURAHAN', 'NM_WP_SPPT', 'ALAMAT_WP']
            
            dtypes = {'KD_PROPINSI': 'int8', 'KD_DATI2': 'int8', 'KD_KECAMATAN': 'int16', 
                      'KD_KELURAHAN': 'int16', 'THN_PAJAK_SPPT': 'int16', 'STATUS_PEMBAYARAN_SPPT': 'int8',
                      'PBB_YG_HARUS_DIBAYAR_SPPT': 'float32'}

            for f in chunk_files:
                chunk = pd.read_csv(f, usecols=lambda c: c in cols_keep, dtype=dtypes, low_memory=False)
                
                # Bikin ID
                chunk['ID_WP_INDIVIDUAL'] = (
                    chunk['KD_PROPINSI'].astype(str).str.zfill(2) + '-' +
                    chunk['KD_DATI2'].astype(str).str.zfill(2) + '-' +
                    chunk['KD_KECAMATAN'].astype(str).str.zfill(3) + '-' +
                    chunk['KD_KELURAHAN'].astype(str).str.zfill(3) + '_' + 
                    chunk['NM_WP_SPPT'].astype(str).str.strip().str.upper() + '_' + 
                    chunk['ALAMAT_WP'].astype(str).str.strip().str.upper()
                )
                # Buang kolom pembentuk ID
                chunk = chunk[['ID_WP_INDIVIDUAL', 'THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'STATUS_PEMBAYARAN_SPPT']]
                dfs.append(chunk)
            
            if dfs:
                df_transaksi = pd.concat(dfs, ignore_index=True)
                
        except Exception as e:
            st.warning(f"Gagal menggabungkan data chunks: {e}")
    
    return df_rfm, df_transaksi

# EKSEKUSI LOAD DATA
try:
    MAIN_DF_RFM, MAIN_DF_TRANSAKSI = load_data()
except Exception as e:
    st.error(f"Error Loading Data: {e}")
    MAIN_DF_RFM, MAIN_DF_TRANSAKSI = None, None

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
# 5. HALAMAN DASHBOARD UTAMA (SEARCH + KPI)
# ==========================================
def show_dashboard(df_rfm, df_trans):
    st.title("📊 SIAP (Sistem Informasi & Analisa Pajak)")
    
    # --- INPUT PENCARIAN ---
    col_search, col_spacer = st.columns([3, 1])
    with col_search:
        query = st.text_input("🔍 Cari WP (Nama / Alamat / ID):", placeholder="Ketik nama WP di sini...").upper()
    
    st.markdown("---")

    # JIKA ADA PENCARIAN -> TAMPILKAN HASIL PENCARIAN
    if query:
        if df_rfm is None: 
            st.error("Data RFM tidak tersedia.")
            return
        
        hasil = df_rfm[
            df_rfm['NAMA_SEARCH'].str.contains(query, na=False) | 
            df_rfm['ID_WP_INDIVIDUAL'].astype(str).str.contains(query, na=False)
        ]
        
        st.subheader(f"Hasil Pencarian: {len(hasil)} WP Ditemukan")
        if len(hasil) == 0: st.warning("Tidak ditemukan.")
        
        for index, row in hasil.head(20).iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.markdown(f"**{row.get('NAMA_WP','-')}**")
                c1.caption(f"{row.get('ALAMAT_WP','-')}")
                
                seg = str(row.get('Segment', '-'))
                if "Berisiko" in seg: c2.error(seg)
                elif "Champions" in seg: c2.success(seg)
                else: c2.info(seg)
                
                c3.metric("Total Bayar", f"Rp {row.get('Monetary',0):,.0f}")
                if c4.button("Detail ➡️", key=f"btn_{index}"):
                    go_to_detail(row['ID_WP_INDIVIDUAL'])
                st.markdown("---")
                
    # JIKA TIDAK ADA PENCARIAN -> TAMPILKAN DASHBOARD EKSEKUTIF
    else:
        if df_rfm is None or df_trans is None:
            st.info("Sedang memuat data Dashboard...")
            return

        # --- KPI METRICS (SNAPSHOT) ---
        tahun_ini = df_trans['THN_PAJAK_SPPT'].max()
        data_tahun_ini = df_trans[df_trans['THN_PAJAK_SPPT'] == tahun_ini]
        total_wp = df_rfm['ID_WP_INDIVIDUAL'].nunique()
        
        bayar_ini = data_tahun_ini[data_tahun_ini['STATUS_PEMBAYARAN_SPPT'] == 1]['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()
        tunggak_ini = data_tahun_ini[data_tahun_ini['STATUS_PEMBAYARAN_SPPT'] == 0]['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()
        target_ini = bayar_ini + tunggak_ini
        total_tunggakan_all = df_trans[df_trans['STATUS_PEMBAYARAN_SPPT'] == 0]['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Wajib Pajak", f"{total_wp:,.0f}")
        k2.metric(f"Realisasi {tahun_ini}", f"Rp {bayar_ini/1e9:,.1f} M", f"{(bayar_ini/target_ini)*100:.1f}%" if target_ini > 0 else "0%")
        k3.metric(f"Potensi Tunggakan {tahun_ini}", f"Rp {tunggak_ini/1e9:,.1f} M", delta_color="inverse")
        k4.metric("Total Tunggakan (Akumulasi)", f"Rp {total_tunggakan_all/1e9:,.1f} M", delta_color="inverse")

        st.markdown("---")
        
        # --- BARIS 2: RFM BAR CHART & PENJELASAN (Layout KSO SCISI) ---
        st.subheader("🗺️ Peta Kekuatan WP (Segmentasi)")
        
        # Siapkan Data Chart
        bar_data = df_rfm.groupby('Segment').agg(
            Count=('ID_WP_INDIVIDUAL', 'count'),
            Monetary=('Monetary', 'sum')
        ).reset_index().sort_values('Count', ascending=True)

        col_chart, col_text = st.columns([2, 1])
        
        with col_chart:
            # Visualisasi Bar Chart Horizontal
            fig_bar = px.bar(
                bar_data,
                x='Count',
                y='Segment',
                orientation='h',
                text='Count',
                color='Monetary',
                color_continuous_scale='Blues',
                title="Jumlah WP per Segmen (Warna = Nilai Kontribusi)",
                labels={'Count': 'Jumlah WP', 'Segment': '', 'Monetary': 'Rupiah'}
            )
            fig_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
            fig_bar.update_layout(height=450, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_text:
            st.markdown("#### 📖 Kamus Segmen")
            with st.expander("💎 Champions (Patuh)", expanded=True):
                st.caption("Selalu bayar tepat waktu, nilai pajak besar.")
                st.markdown(":green[**Action:**] *Pertahankan (Retensi).*")
            with st.expander("🚨 At Risk (Berisiko)"):
                st.caption("Dulu aktif, baru-baru ini berhenti bayar.")
                st.markdown(":red[**Action:**] *Kunjungan Prioritas!*")
            with st.expander("💤 Sleeping (Tidur)"):
                st.caption("Sudah lama tidak bayar (>3 tahun).")
                st.markdown(":orange[**Action:**] *Cek Lapangan / Pemutihan.*")
            with st.expander("🌱 New / Potensial"):
                st.caption("WP Baru atau mulai rajin.")
                st.markdown(":blue[**Action:**] *Edukasi & Reminder.*")

        st.markdown("---")
        
        # --- BARIS 3: DONUT CHART & TOP 5 ---
        c_pie, c_table = st.columns([1, 2])
        
        with c_pie:
            st.subheader(f"💸 Status {tahun_ini}")
            labels = ['Lunas', 'Menunggak']
            values = [bayar_ini, tunggak_ini]
            colors = ['#2ecc71', '#e74c3c']
            fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=colors)])
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c_table:
            st.subheader("🏆 Top 5 WP (Kakap) per Kategori")
            tab1, tab2, tab3 = st.tabs(["💎 Champions", "🚨 At Risk", "💤 Sleeping"])
            
            with tab1:
                top = df_rfm[df_rfm['Segment'].str.contains('Champions', na=False)].nlargest(5, 'Monetary')
                st.dataframe(top[['NAMA_WP', 'ALAMAT_WP', 'Monetary']].style.format({'Monetary': 'Rp {:,.0f}'}), use_container_width=True, hide_index=True)
            with tab2:
                top = df_rfm[df_rfm['Segment'].str.contains('Berisiko', na=False)].nlargest(5, 'Monetary')
                st.dataframe(top[['NAMA_WP', 'ALAMAT_WP', 'Monetary']].style.format({'Monetary': 'Rp {:,.0f}'}), use_container_width=True, hide_index=True)
            with tab3:
                top = df_rfm[df_rfm['Segment'].str.contains('Tidur', na=False)].nlargest(5, 'Monetary')
                st.dataframe(top[['NAMA_WP', 'ALAMAT_WP', 'Monetary']].style.format({'Monetary': 'Rp {:,.0f}'}), use_container_width=True, hide_index=True)

# ==========================================
# 6. HALAMAN DETAIL
# ==========================================
def show_detail_page(df_rfm, df_trans):
    wp_id = st.session_state.selected_id
    
    if df_rfm is None: return
    profil_data = df_rfm[df_rfm['ID_WP_INDIVIDUAL'] == wp_id]
    if profil_data.empty:
        st.error("Data tidak ditemukan."); st.button("Kembali", on_click=go_back); return

    profil = profil_data.iloc[0]
    
    st.button("⬅️ Kembali ke Dashboard", on_click=go_back)
    st.title(f"👤 {profil.get('NAMA_WP','-')}")
    st.caption(f"ID: {wp_id}"); st.info(f"📍 {profil.get('ALAMAT_WP','-')}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Segmen", profil.get('Segment','-'))
    c2.metric("Monetary", f"Rp {profil.get('Monetary',0):,.0f}")
    c3.metric("Frequency", f"{profil.get('Frequency',0)} Kali")
    c4.metric("Recency", f"{profil.get('Recency',0)} Hari")

    st.markdown("---")
    
    if df_trans is not None:
        histori = df_trans[df_trans['ID_WP_INDIVIDUAL'] == wp_id].sort_values('THN_PAJAK_SPPT')
        if not histori.empty:
            histori['Status'] = histori['STATUS_PEMBAYARAN_SPPT'].map({1:'Lunas', 0:'Tunggakan'})
            fig = px.bar(histori, x='THN_PAJAK_SPPT', y='PBB_YG_HARUS_DIBAYAR_SPPT', color='Status',
                         color_discrete_map={'Lunas':'#2ecc71', 'Tunggakan':'#e74c3c'})
            st.plotly_chart(fig, use_container_width=True)
            
            view = histori[['THN_PAJAK_SPPT','PBB_YG_HARUS_DIBAYAR_SPPT','Status']]
            st.dataframe(view, use_container_width=True, hide_index=True)
        else: st.info("Tidak ada data transaksi.")

# ==========================================
# 7. MAIN ROUTING (FIXED)
# ==========================================
if st.session_state.selected_id is not None:
    show_detail_page(MAIN_DF_RFM, MAIN_DF_TRANSAKSI)
else:
    show_dashboard(MAIN_DF_RFM, MAIN_DF_TRANSAKSI)