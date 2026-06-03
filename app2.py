import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from sklearn.cluster import KMeans
import os

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Dashboard Peta Growth Cabang PGI",
    page_icon="",
    layout="wide"
)

st.title("Analisis Spasial & Growth Cabang PGI")
st.markdown("Aplikasi ini menampilkan visualisasi data sebaran growth cabang dan pengelompokan wilayah.")

# --- MENDAPATKAN DATA ---
# Menggunakan sidebar untuk fleksibilitas: Bisa baca file default atau upload baru
st.sidebar.header("Pengaturan Data")
uploaded_file = st.sidebar.file_uploader("Upload File Performa Cabang (Excel)", type=["xlsx"])

@st.cache_data
def load_data(file_path_or_buffer):
    try:
        df = pd.read_excel(file_path_or_buffer)
        return df
    except Exception as e:
        st.error(f"Gagal membaca data: {e}")
        return None

# Cek sumber data
if uploaded_file is not None:
    df_clean = load_data(uploaded_file)
else:
    # Path default di lokal/GitHub repo
    default_path = 'data/performa-cabang.xlsx'
    if os.path.exists(default_path):
        df_clean = load_data(default_path)
    else:
        st.info("Silakan upload file `.xlsx` Anda melalui sidebar untuk memulai analisis.")
        st.stop()

if df_clean is not None:
    # Menampilkan preview data di expander
    with st.expander("Lihat Preview Data Mentah"):
        st.dataframe(df_clean.head(), use_container_width=True)

    # --- KMEANS CLUSTERING (INTERAKTIF) ---
    st.sidebar.subheader("Konfigurasi Klasterisasi")
    k = st.sidebar.slider("Jumlah Klaster (K-Means)", min_value=2, max_value=10, value=3)
    
    # Proses clustering silang koordinat
    X = df_clean[['latitude_cabang', 'longitude_cabang']]
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    df_clean['cluster'] = kmeans.fit_predict(X)

    # --- PEMBUATAN PETA FOLIUM ---
    st.subheader("Peta Interaktif Sebaran Cabang")
    
    # Inisialisasi Map Utama
    map_center = [df_clean['latitude_cabang'].mean(), df_clean['longitude_cabang'].mean()]
    m = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB positron')

    # Layer 1: Heatmap Growth
    fg1 = folium.FeatureGroup(name='Heatmap Sebaran Growth')
    heat_omzet = [[row['latitude_cabang'], row['longitude_cabang'], row['Growth']] for i, row in df_clean.iterrows()]
    HeatMap(heat_omzet, radius=15, blur=20, gradient={0.4: 'blue', 0.7: 'lime', 1: 'yellow'}).add_to(fg1)

    # Deteksi nama kolom (antisipasi typo Mei25 vs Mei26 di script asal)
    col_jan = 'Omset Jan25' if 'Omset Jan25' in df_clean.columns else df_clean.columns[2]
    col_mei = 'Omset Mei26' if 'Omset Mei26' in df_clean.columns else ('Omset Mei25' if 'Omset Mei25' in df_clean.columns else df_clean.columns[3])

    # Layer 2a: Sebaran Positive Growth
    fg_positive_growth = folium.FeatureGroup(name='Positive Growth', show=True)
    # Layer 2b: Sebaran Negative Growth
    fg_negative_growth = folium.FeatureGroup(name='Negative Growth', show=True)

    for i, row in df_clean.iterrows():
        # Membuat popup HTML yang aman
        popup_text = f"""
        <b>Cabang:</b> {row['cabang']}<br>
        <b>Cluster Wilayah:</b> {row['cluster']}<br>
        <b>Omzet Jan:</b> Rp {row[col_jan]:,.0f}<br>
        <b>Omzet Mei:</b> Rp {row[col_mei]:,.0f}<br>
        <b>Growth:</b> <span style='color:{"green" if row["Growth"] >= 0 else "red"};'>Rp {row["Growth"]:,.0f}</span>
        """
        
        marker_color = 'green' if row['Growth'] >= 0 else 'red'
        target_fg = fg_positive_growth if row['Growth'] >= 0 else fg_negative_growth
        
        folium.CircleMarker(
            location=[row['latitude_cabang'], row['longitude_cabang']],
            radius=6,
            color=marker_color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(target_fg)

    # Masukkan semua layer ke peta
    fg1.add_to(m)
    fg_positive_growth.add_to(m)
    fg_negative_growth.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # Legend HTML kustom (disesuaikan posisinya agar pas di layar web)
    legend_html = '''
         <div style="position: fixed; 
                     bottom: 30px; left: 30px; width: 180px; height: 75px; 
                     border:2px solid grey; z-index:9999; font-size:12px;
                     background-color:white; opacity:0.85; padding: 5px;
                     border-radius: 5px;
                     ">
           <b>Keterangan Tren:</b> <br>
           &nbsp; <i style="background:green; width:12px; height:12px; display:inline-block; border-radius:50%;"></i>&nbsp; Positive Growth <br>
           &nbsp; <i style="background:red; width:12px; height:12px; display:inline-block; border-radius:50%;"></i>&nbsp; Negative Growth <br>
         </div>
         '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Tampilkan Peta di Streamlit
    st_folium(m, width=1100, height=550, returned_objects=[])

    # --- STATISTIK TAMBAHAN ---
    st.markdown("---")
    st.subheader("Ringkasan Cluster Geografis")
    
    # Grouping ringkas berdasarkan cluster yang terbentuk dari koordinat
    summary_cluster = df_clean.groupby('cluster').agg(
        Jumlah_Cabang=('cabang', 'count'),
        Total_Growth=('Growth', 'sum'),
        Rata_Rata_Growth=('Growth', 'mean')
    ).reset_index()
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(summary_cluster.style.format({
            'Total_Growth': 'Rp {:,.0f}',
            'Rata_Rata_Growth': 'Rp {:,.0f}'
        }), use_container_width=True)
    with col2:
        st.info(f"Peta di atas mengelompokkan cabang menjadi **{k} cluster** berdasarkan kedekatan wilayah geografisnya (Latitude & Longitude).")
