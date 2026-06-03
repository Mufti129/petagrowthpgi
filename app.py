import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import os

# 1. Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Dashboard Peta Performa & Growth PGI",
    page_icon="",
    layout="wide"
)

st.title("Analisis Spasial Performa & Growth Cabang PGI")
st.markdown("Aplikasi ini memetakan sebaran kontribusi growth serta kategorisasi performa setiap cabang PGI secara interaktif.")

# --- MENDAPATKAN DATA ---
st.sidebar.header("⚙️ Pengaturan Data")
uploaded_file = st.sidebar.file_uploader("Upload File Performa Cabang (Excel)", type=["xlsx"])

@st.cache_data
def load_data(file_path_or_buffer):
    try:
        df = pd.read_excel(file_path_or_buffer)
        return df
    except Exception as e:
        st.error(f"Gagal membaca data: {e}")
        return None

# Cek sumber data (Uploader vs File Lokal)
if uploaded_file is not None:
    df_clean = load_data(uploaded_file)
else:
    default_path = 'data/performa-cabang.xlsx'
    if os.path.exists(default_path):
        df_clean = load_data(default_path)
    else:
        st.info("Silakan unggah file `performa-cabang.xlsx` melalui sidebar untuk menampilkan peta.")
        st.stop()

if df_clean is not None:
    # Preview Data Tambahan
    with st.expander("👀 Lihat Preview Data"):
        st.dataframe(df_clean.head(), use_container_width=True)

    # Antisipasi jika ada perbedaan penamaan kolom atau typo bawaan file (Jan25 vs Mei26)
    col_jan = 'Omset Jan25' if 'Omset Jan25' in df_clean.columns else df_clean.columns[2]
    col_mei = 'Omset Mei26' if 'Omset Mei26' in df_clean.columns else ('Omset Mei25' if 'Omset Mei25' in df_clean.columns else df_clean.columns[3])

    # --- INGEREGRASIKAN PETA FOLIUM ---
    st.subheader("Peta Interaktif Sebaran Cabang")
    
    # Inisialisasi Map Utama di titik tengah koordinat cabang
    map_center = [df_clean['latitude_cabang'].mean(), df_clean['longitude_cabang'].mean()]
    m = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB positron')

    # Layer 1: Heatmap Growth
    fg1 = folium.FeatureGroup(name='Heatmap Sebaran Growth', show=False)
    heat_omzet = [[row['latitude_cabang'], row['longitude_cabang'], row['Growth']] for i, row in df_clean.iterrows()]
    HeatMap(heat_omzet, radius=15, blur=20, gradient={0.4: 'blue', 0.7: 'lime', 1: 'yellow'}).add_to(fg1)

    # Layer 2a & 2b: Berdasarkan Tren Growth (Default sembunyikan agar tidak menumpuk dengan kategori)
    fg_positive_growth = folium.FeatureGroup(name='Tren: Positive Growth', show=False)
    fg_negative_growth = folium.FeatureGroup(name='Tren: Negative Growth', show=False)

    # Layer 3a - 3d: Berdasarkan Variabel Kategori Baru (Default tampilkan)
    fg_sangat_baik = folium.FeatureGroup(name='Kategori: Sangat Baik', show=True)
    fg_baik = folium.FeatureGroup(name='Kategori: Baik', show=True)
    fg_kurang_baik = folium.FeatureGroup(name='Kategori: Kurang Baik', show=True)
    fg_jelek = folium.FeatureGroup(name='Kategori: Jelek', show=True)

    # Definisi warna kategori sesuai script terbaru Anda
    category_colors = {
        'sangat baik': 'blue',
        'baik': 'green',
        'kurang baik': 'orange',
        'jelek': 'red'
    }

    # Perulangan untuk memetakan marker ke masing-masing FeatureGroup
    for i, row in df_clean.iterrows():
        # Membangun popup HTML yang memuat semua variabel baru
        popup_content = f"""
        <div style='font-family: Arial, sans-serif; font-size: 12px; min-width: 180px;'>
            <b>Cabang:</b> {row['cabang']}<br>
            <b>Kategori:</b> <span style='font-weight:bold;'>{row['Kategori']}</span><br><hr style='margin:4px 0;'>
            <b>Omzet Jan25:</b> Rp {row[col_jan]:,.0f}<br>
            <b>Omzet Mei25:</b> Rp {row[col_mei]:,.0f}<br>
            <b>Growth:</b> <span style='color:{"green" if row["Growth"] >= 0 else "red"}; font-weight:bold;'>Rp {row["Growth"]:,.0f}</span><br>
            <b>Persen Growth:</b> {row['Persen Growth']}
        </div>
        """
        
        # 1. Plotting ke Group Tren (Positive / Negative)
        trend_color = 'green' if row['Growth'] >= 0 else 'red'
        target_trend_fg = fg_positive_growth if row['Growth'] >= 0 else fg_negative_growth
        
        folium.CircleMarker(
            location=[row['latitude_cabang'], row['longitude_cabang']],
            radius=5,
            color=trend_color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_content, max_width=300)
        ).add_to(target_trend_fg)

        # 2. Plotting ke Group Kategori Baru
        kategori_clean = str(row['Kategori']).strip().lower()
        marker_color = category_colors.get(kategori_clean, 'gray')

        marker_kategori = folium.CircleMarker(
            location=[row['latitude_cabang'], row['longitude_cabang']],
            radius=5,
            color=marker_color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_content, max_width=300)
        )

        if kategori_clean == 'sangat baik':
            marker_kategori.add_to(fg_sangat_baik)
        elif kategori_clean == 'baik':
            marker_kategori.add_to(fg_baik)
        elif kategori_clean == 'kurang baik':
            marker_kategori.add_to(fg_kurang_baik)
        elif kategori_clean == 'jelek':
            marker_kategori.add_to(fg_jelek)

    # Masukkan seluruh komponen layer ke peta
    fg1.add_to(m)
    fg_positive_growth.add_to(m)
    fg_negative_growth.add_to(m)
    fg_sangat_baik.add_to(m)
    fg_baik.add_to(m)
    fg_kurang_baik.add_to(m)
    fg_jelek.add_to(m)

    # Tambahkan kontrol layer di pojok kanan atas peta
    folium.LayerControl(collapsed=False).add_to(m)

    # Penyesuaian Legend HTML agar tampil rapi di container web Streamlit
    legend_html = '''
         <div style="position: fixed; 
                     bottom: 30px; left: 30px; width: 190px; height: auto; 
                     border:2px solid grey; z-index:9999; font-size:12px;
                     background-color:white; opacity:0.85; padding: 8px;
                     border-radius: 5px; font-family: Arial, sans-serif;
                     ">
           <b>Growth Marker Color</b> <br>
           <i style="background:green; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Positive Growth <br>
           <i style="background:red; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Negative Growth <br>
           <b style="display:inline-block; margin-top:5px;">Category Marker Color</b> <br>
           <i style="background:blue; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Sangat Baik <br>
           <i style="background:green; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Baik <br>
           <i style="background:orange; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Kurang Baik <br>
           <i style="background:red; width:10px; height:10px; display:inline-block; border-radius:50%;"></i>&nbsp; Jelek <br>
         </div>
         '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Tampilkan objek peta ke web interface Streamlit
    st_folium(m, width=1100, height=600, returned_objects=[])

    # --- ANALISIS WRAPPER / RINGKASAN ---
    st.markdown("---")
    st.subheader("Analisis Distribusi Kategori Performa")
    
    # Tampilkan matriks jumlah cabang per kategori secara dinamis
    if 'Kategori' in df_clean.columns:
        col1, col2 = st.columns([1, 2])
        with col1:
            summary_cat = df_clean['Kategori'].value_index if hasattr(df_clean['Kategori'], 'value_index') else df_clean['Kategori'].value_counts()
            st.dataframe(summary_cat, use_container_width=True)
        with col2:
            avg_growth = df_clean.groupby('Kategori')['Growth'].mean().reset_index()
            st.markdown("**Rata-rata Nilai Growth per Kategori:**")
            st.dataframe(avg_growth.style.format({'Growth': 'Rp {:,.0f}'}), use_container_width=True)
