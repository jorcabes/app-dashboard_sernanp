import streamlit as st
import pandas as pd
import plotly.express as px
import geopandas as gpd
import json
import folium
import numpy as np
from streamlit_folium import st_folium
import branca.colormap as cm

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Dashboard Turismo SERNANP",
    layout="wide"
)

st.title("🌿 Dashboard Turismo SERNANP")

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data
def load_data():

    df = pd.read_csv(
        "SERNANPdataset_Turismo.csv",
        encoding="latin1"
    )

    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%Y%m%d")

    df["TOTAL_VISITAS"] = (
        df["VISITAS_E1"] +
        df["VISITAS_E2A3"] +
        df["VISITAS_E3A30"]
    )

    df["MES"] = df["FECHA"].dt.month
    df["ANIO"] = df["FECHA"].dt.year
    df["MES_NOMBRE"] = df["FECHA"].dt.strftime("%b")

    return df

df = load_data()

# =========================================================
# GEOJSON
# =========================================================
with open("anp.geojson", "r", encoding="utf-8") as f:
    anp_geo = json.load(f)


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Filtros")

departamentos = st.sidebar.multiselect(
    "Departamento",
    sorted(df["DEPARTAMENTO"].dropna().unique()),
    default=sorted(df["DEPARTAMENTO"].dropna().unique())
)

anios = st.sidebar.multiselect(
    "Año",
    sorted(df["ANIO"].unique()),
    default=sorted(df["ANIO"].unique())
)

filtered_df = df[
    (df["DEPARTAMENTO"].isin(departamentos)) &
    (df["ANIO"].isin(anios))
]

# =========================================================
# KPIs AVANZADOS
# =========================================================
total_visitas = filtered_df["TOTAL_VISITAS"].sum()

promedio_mensual = (
    filtered_df
    .groupby("FECHA")["TOTAL_VISITAS"]
    .sum()
    .mean()
)

top_departamento = (
    filtered_df
    .groupby("DEPARTAMENTO")["TOTAL_VISITAS"]
    .sum()
    .idxmax()
)

top_anp = (
    filtered_df
    .groupby("ANP")["TOTAL_VISITAS"]
    .sum()
    .idxmax()
)

# Crecimiento mensual
monthly = (
    filtered_df
    .groupby("FECHA")["TOTAL_VISITAS"]
    .sum()
    .reset_index()
)

growth = monthly["TOTAL_VISITAS"].pct_change().mean() * 100

# =========================================================
# KPIs
# =========================================================
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("👥 Total Visitas", f"{total_visitas:,.0f}")

col2.metric(
    "📅 Promedio Mensual",
    f"{promedio_mensual:,.0f}"
)

col3.metric(
    "🏆 Top Departamento",
    top_departamento
)

col4.metric(
    "🌿 ANP Más Visitada",
    top_anp
)

col5.metric(
    "📈 Crecimiento Promedio",
    f"{growth:.2f}%"
)

st.markdown("---")

# =========================================================
# GRAFICO 1
# =========================================================
st.subheader("📈 Evolución Temporal")

fig1 = px.line(
    monthly,
    x="FECHA",
    y="TOTAL_VISITAS",
    markers=True
)

st.plotly_chart(fig1, use_container_width=True)

# =========================================================
# GRAFICO 2
# =========================================================
st.subheader("🏞️ Top 10 ANP")

top10 = (
    filtered_df
    .groupby("ANP")["TOTAL_VISITAS"]
    .sum()
    .reset_index()
    .sort_values(by="TOTAL_VISITAS", ascending=False)
    .head(10)
)

fig2 = px.bar(
    top10,
    x="TOTAL_VISITAS",
    y="ANP",
    orientation="h"
)

fig2.update_layout(yaxis={'categoryorder':'total ascending'})

st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# GRAFICO 3
# =========================================================
st.subheader("🌎 Procedencia")

proc = (
    filtered_df
    .groupby("PROCEDENCIA")["TOTAL_VISITAS"]
    .sum()
    .reset_index()
)

fig3 = px.pie(
    proc,
    names="PROCEDENCIA",
    values="TOTAL_VISITAS"
)

st.plotly_chart(fig3, use_container_width=True)

# =========================================================
# LEER GEOJSON ANP
# =========================================================
gdf = gpd.read_file("anp.geojson")

# =========================================================
# AGRUPAR VISITAS POR ANP
# =========================================================
df.columns = df.columns.str.lower().str.strip()
gdf.columns = gdf.columns.str.lower().str.strip()

anp_visitas = (
    filtered_df
    .groupby("anp_codi")["TOTAL_VISITAS"]
    .sum()
    .reset_index()
)

# =========================================================
# NORMALIZAR TEXTO
# =========================================================
gdf["anp_codi"] = gdf["anp_codi"].str.upper().str.strip()
anp_visitas["anp_codi"] = anp_visitas["anp_codi"].str.upper().str.strip()

# ======================================================
# JOIN
# ======================================================
gdf = gdf.merge(
    anp_visitas,
    on="anp_codi",
    how="left"
)

gdf["TOTAL_VISITAS"] = gdf["TOTAL_VISITAS"].fillna(0)

# ======================================================
# NORMALIZACIÓN
# ======================================================
gdf["visitas_norm"] = np.log1p(gdf["TOTAL_VISITAS"])

# ======================================================
# GDF LIMPIO PARA EL MAPA
# ======================================================
gdf_map = gdf[[
    "anp_codi",
    "anp_nomb",
    "TOTAL_VISITAS",
    "visitas_norm",
    "geometry"
]].copy()

# ======================================================
# CENTRO DEL MAPA
# ======================================================
center = gdf_map.geometry.centroid

lat = center.y.mean()
lon = center.x.mean()

# ======================================================
# BASEMAP
# ======================================================
basemap = st.sidebar.selectbox(
    "Basemap",
    [
        "OpenStreetMap",
        "CartoDB positron",
        "CartoDB dark_matter",
        "Stamen Terrain"
    ]
)

m = folium.Map(
    location=[lat, lon],
    zoom_start=5,
    tiles=basemap
)

# ======================================================
# COLORMAP
# ======================================================
min_visitas = gdf_map["TOTAL_VISITAS"].min()
max_visitas = gdf_map["TOTAL_VISITAS"].max()

colormap = cm.linear.YlGn_09.scale(
    min_visitas,
    max_visitas
)

colormap.caption = "Total de Visitas"

# ======================================================
# ESTILO
# ======================================================
def style_function(feature):

    visitas_reales = feature["properties"]["TOTAL_VISITAS"]

    visitas_norm = np.log1p(visitas_reales)

    max_norm = np.log1p(max_visitas)

    color_value = (
        visitas_norm / max_norm
    ) * max_visitas

    return {
        "fillColor": colormap(color_value),
        "color": "black",
        "weight": 0.5,
        "fillOpacity": 0.8,
    }

# ======================================================
# TOOLTIP
# ======================================================
tooltip = folium.GeoJsonTooltip(
    fields=["anp_nomb", "TOTAL_VISITAS"],
    aliases=["ANP:", "Visitas:"],
    localize=True
)

# ======================================================
# CAPA GEOJSON
# ======================================================
geojson = folium.GeoJson(
    gdf_map,
    style_function=style_function,
    tooltip=tooltip
)

geojson.add_to(m)

# ======================================================
# LEYENDA
# ======================================================
colormap.add_to(m)

# ======================================================
# MOSTRAR MAPA
# ======================================================
st.subheader("🗺️ Visitas Normalizadas por ANP")

st_folium(
    m,
    width=1200,
    height=700
)

# =========================================================
# TABLA
# =========================================================
st.subheader("📋 Datos")

st.dataframe(filtered_df)