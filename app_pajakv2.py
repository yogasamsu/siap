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
    try:
        RAHASIA = st.secrets["password"]
    except:
        RAHASIA = "admin123" 

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
# 3. LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    # A. LOAD RFM
    path_rfm = 'hasil_rfm_individu_final.csv'
    df_rfm = None
    if os.path.exists(path_rfm):
        try:
            df_rfm = pd.read_csv(path_rfm)
            if 'NAMA_WP' not in df_rfm.columns: df_rfm['NAMA_WP'] = "WP-" + df_rfm.index.astype(str)
            df_rfm['NAMA_SEARCH'] = df_rfm['NAMA_WP'].fillna('').astype(str).str.upper()
            if 'ID_WP_INDIVIDUAL' not in df_rfm.columns: df_rfm['ID_WP_INDIVIDUAL'] = df_rfm.index
        except Exception as e:
            st.error(f"Gagal load RFM: {e}")

    # B. LOAD TRANSAKSI
    df_transaksi = None
    chunk_files = glob.glob("data_chunks/data_part_*.csv")
    if not chunk_files: chunk_files = glob.glob("data_part_*.csv")

    if chunk_files:
        try:
            chunk_files.sort()
            dfs = []
            cols = ['THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'STATUS_PEMBAYARAN_SPPT', 
                    'ID_WP_INDIVIDUAL', 'KD_KECAMATAN', 'KD_KELURAHAN', 'NM_WP_SPPT', 'ALAMAT_WP', 'KD_PROPINSI', 'KD_DATI2']
            dtypes = {'STATUS_PEMBAYARAN_SPPT': 'int8', 'PBB_YG_HARUS_DIBAYAR_SPPT': 'float32', 
                      'THN_PAJAK_SPPT': 'int16', 'KD_KECAMATAN': 'int16', 'KD_KELURAHAN': 'int16'}

            for f in chunk_files:
                chunk = pd.read_csv(f, usecols=lambda c: c in cols, dtype=dtypes, low_memory=False)
                chunk['ID_WP_INDIVIDUAL'] = (
                    chunk['KD_PROPINSI'].astype(str).str.zfill(2) + '-' +
                    chunk['KD_DATI2'].astype(str).str.zfill(2) + '-' +
                    chunk['KD_KECAMATAN'].astype(str).str.zfill(3) + '-' +
                    chunk['KD_KELURAHAN'].astype(str).str.zfill(3) + '_' + 
                    chunk['NM_WP_SPPT'].astype(str).str.strip().str.upper() + '_' + 
                    chunk['ALAMAT_WP'].astype(str).str.strip().str.upper()
                )
                chunk = chunk[['ID_WP_INDIVIDUAL', 'THN_PAJAK_SPPT', 'PBB_YG_HARUS_DIBAYAR_SPPT', 'STATUS_PEMBAYARAN_SPPT']]
                dfs.append(chunk)
            
            if dfs:
                df_transaksi = pd.concat(dfs, ignore_index=True)
        except Exception as e:
            st.warning(f"Gagal load transaksi: {e}")
            
    return df_rfm, df_transaksi

try:
    MAIN_DF_RFM, MAIN_DF_TRANSAKSI = load_data()
except Exception as e:
    st.error(f"Error: {e}")
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
# 5. HALAMAN DASHBOARD (UPDATE FILTER TAHUN)
# ==========================================
def show_dashboard(df_rfm, df_trans):
    st.title("📊 SIAP (Sitem Informasi & Analisa Pajak)")
    
    # --- INPUT PENCARIAN ---
    col_search, col_spacer = st.columns([3, 1])
    with col_search:
        query = st.text_input("🔍 Cari WP (Nama / Alamat / ID):", placeholder="Ketik nama WP di sini...").upper()
    
    st.markdown("---")

    if query:
        # (Kode Pencarian Tetap Sama...)
        if df_rfm is None: return
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
                
    else:
        if df_rfm is None or df_trans is None:
            st.info("Sedang memuat data...")
            return

        # --- FILTER TAHUN (BARU!) ---
        # Ambil daftar tahun unik dari data transaksi
        list_tahun = sorted(df_trans['THN_PAJAK_SPPT'].unique(), reverse=True)
        list_tahun_str = [str(t) for t in list_tahun]
        
        # Tambahkan Opsi "Semua Periode"
        opsi_tahun = ['Semua Periode'] + list_tahun_str
        
        col_filter, col_dummy = st.columns([1, 3])
        with col_filter:
            pilihan_tahun = st.selectbox("📅 Filter Tahun Pajak:", opsi_tahun)

        # --- LOGIKA FILTERING DATA ---
        if pilihan_tahun == 'Semua Periode':
            # Jika Semua, hitung akumulasi
            data_filtered = df_trans
            label_kpi = "Total (Semua Tahun)"
        else:
            # Jika Tahun Spesifik, filter data transaksi
            thn_int = int(pilihan_tahun)
            data_filtered = df_trans[df_trans['THN_PAJAK_SPPT'] == thn_int]
            label_kpi = f"Tahun {pilihan_tahun}"

        # --- KPI METRICS (DINAMIS SESUAI FILTER) ---
        total_wp = df_rfm['ID_WP_INDIVIDUAL'].nunique()
        
        # Hitung Realisasi vs Tunggakan dari data_filtered
        bayar_ini = data_filtered[data_filtered['STATUS_PEMBAYARAN_SPPT'] == 1]['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()
        tunggak_ini = data_filtered[data_filtered['STATUS_PEMBAYARAN_SPPT'] == 0]['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()
        target_ini = bayar_ini + tunggak_ini
        
        # Hitung Tunggakan Total (Selalu Akumulasi agar user tetap aware beban hutang global)
        total_tunggakan_all = df_trans[df_trans['STATUS_PEMBAYARAN_SPPT'] == 0]['PBB_YG_HARUS_DIBAYAR_SPPT'].sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Wajib Pajak", f"{total_wp:,.0f}")
        
        # KPI Dinamis
        #persen = (bayar_ini/target_ini)*100 if target_ini > 0 else 0
        # (KODE BARU)
        k2.metric(f"Realisasi {tahun_ini}", f"Rp {bayar_ini/1e9:,.1f} M")
        k3.metric(f"Potensi Tunggakan {tahun_ini}", f"Rp {tunggak_ini/1e9:,.1f} M")
        #k2.metric(f"Realisasi ({label_kpi})", f"Rp {bayar_ini/1e9:,.1f} M", f"{persen:.1f}%")
        #k3.metric(f"Tunggakan ({label_kpi})", f"Rp {tunggak_ini/1e9:,.1f} M", delta_color="inverse")
        
        # KPI Statis (Beban Hutang Global)
        k4.metric("Total Tunggakan (Akumulasi)", f"Rp {total_tunggakan_all/1e9:,.1f} M", delta_color="inverse")

        st.markdown("---")
        
        # --- BARIS 2: RFM BAR CHART (TETAP) ---
        # Segmentasi tidak berubah walau tahun difilter (karena RFM butuh history)
        st.subheader("🗺️ Peta Kekuatan WP (Segmentasi)")
        
        bar_data = df_rfm.groupby('Segment').agg(
            Count=('ID_WP_INDIVIDUAL', 'count'),
            Monetary=('Monetary', 'sum')
        ).reset_index().sort_values('Count', ascending=True)

        color_map = {
            'WP Patuh Terbaik (Champions)': '#2ecc71', 
            'WP Patuh (Nilai Kecil)': '#82e0aa',       
            'WP Baru (New)': '#3498db',                
            'WP Potensial (Potential)': '#f1c40f',     
            'WP Lainnya (Need Attention)': '#95a5a6',  
            'WP Tidur (Nilai Kecil)': '#e67e22',       
            'WP Tidur (Nilai Besar)': '#d35400',       
            'WP Berisiko (At Risk)': '#e74c3c'         
        }
        urutan = [
            'WP Patuh Terbaik (Champions)', 'WP Patuh (Nilai Kecil)', 'WP Baru (New)', 
            'WP Potensial (Potential)', 'WP Lainnya (Need Attention)', 
            'WP Tidur (Nilai Kecil)', 'WP Tidur (Nilai Besar)', 'WP Berisiko (At Risk)'
        ]
        
        col_chart, col_text = st.columns([2, 1])
        with col_chart:
            fig_bar = px.bar(
                bar_data, x='Count', y='Segment', orientation='h', text='Count',
                color='Segment', color_discrete_map=color_map, category_orders={'Segment': urutan},
                title="Komposisi Wajib Pajak (Hijau=Aman, Merah=Bahaya)", labels={'Count': 'Jumlah WP', 'Segment': ''}
            )
            fig_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
            fig_bar.update_layout(height=450, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_text:
            st.markdown("#### 📖 Panduan Strategi")
            with st.expander("🟢 ZONA HIJAU", expanded=True): st.caption("Strategi: Apresiasi & Retensi."); st.write("**Champions & Patuh**")
            with st.expander("🟡 ZONA KUNING"): st.caption("Strategi: Edukasi & Reminder."); st.write("**Potensial & Baru**")
            with st.expander("🔴 ZONA MERAH"): st.caption("Strategi: Kunjungan & Penagihan."); st.write("**Berisiko & Tidur**")

        st.markdown("---")
        
        # --- BARIS 3: DONUT CHART (DINAMIS) & TOP 5 ---
        c_pie, c_table = st.columns([1, 2])
        
        with c_pie:
            st.subheader(f"💸 Status ({label_kpi})")
            labels = ['Lunas', 'Menunggak']
            values = [bayar_ini, tunggak_ini]
            colors = ['#2ecc71', '#e74c3c']
            
            # Handle jika data kosong
            if sum(values) == 0:
                st.info("Tidak ada data tagihan pada tahun ini.")
            else:
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
# 6. HALAMAN DETAIL (TETAP SAMA)
# ==========================================
def show_detail_page(df_rfm, df_trans):
    wp_id = st.session_state.selected_id
    
    if df_rfm is None: return
    profil_data = df_rfm[df_rfm['ID_WP_INDIVIDUAL'] == wp_id]
    if profil_data.empty: st.error("Data tidak ditemukan."); st.button("Kembali", on_click=go_back); return

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
# 7. MAIN ROUTING
# ==========================================
if st.session_state.selected_id is not None:
    show_detail_page(MAIN_DF_RFM, MAIN_DF_TRANSAKSI)
else:
    show_dashboard(MAIN_DF_RFM, MAIN_DF_TRANSAKSI)