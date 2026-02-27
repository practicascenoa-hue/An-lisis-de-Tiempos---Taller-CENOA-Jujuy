import streamlit as st
import pandas as pd

# ---------------- CONFIGURACION ----------------

st.set_page_config(page_title="Portal Taller CENOA", layout="wide")

st.title("Portal Taller CENOA")
st.subheader("Análisis de Tiempo - Daño C")

# ---------------- CARGA DE DATOS ----------------

SHEET_ID = "1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8"

# ⚠️ REEMPLAZAR POR EL GID REAL DE LA HOJA "Tipo de Daños (A,B,C)"
GID = "99557603"

url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data
def cargar_datos():
    return pd.read_csv(url)

try:
    df = cargar_datos()
except:
    st.error("Error al cargar la hoja. Verificar permisos o GID.")
    st.stop()

# ---------------- FILTRAR DAÑO C ----------------

df_c = df[df["Tipo de Daño"] == "C"].copy()

if df_c.empty:
    st.warning("No hay registros con Daño C")
    st.stop()

# Convertir tiempo a numérico
df_c["Dif (2)"] = pd.to_numeric(df_c["Dif (2)"], errors="coerce")

# ---------------- KPI PRINCIPALES ----------------

st.markdown("### Indicadores Generales")

col1, col2, col3 = st.columns(3)

col1.metric("Cantidad Registros Daño C", len(df_c))
col2.metric("Promedio General (Horas)", round(df_c["Dif (2)"].mean(), 2))
col3.metric("Total Horas Acumuladas", round(df_c["Dif (2)"].sum(), 2))

# ---------------- ANALISIS POR ETAPA ----------------

st.markdown("### Promedio de Horas por Etapa")

resumen_etapas = (
    df_c
    .groupby("Etapas")["Dif (2)"]
    .mean()
    .reset_index()
    .sort_values(by="Dif (2)", ascending=False)
)

st.dataframe(resumen_etapas, use_container_width=True)
st.bar_chart(resumen_etapas.set_index("Etapas"))

# ---------------- ANALISIS POR PATENTE ----------------

st.markdown("### Tiempo Total por Vehículo (Patente)")

resumen_patente = (
    df_c
    .groupby("Patente")["Dif (2)"]
    .sum()
    .reset_index()
    .sort_values(by="Dif (2)", ascending=False)
)

st.dataframe(resumen_patente, use_container_width=True)
st.bar_chart(resumen_patente.set_index("Patente"))

# ---------------- DETALLE ----------------

st.markdown("### Detalle Completo - Daño C")
st.dataframe(df_c[["Patente", "Etapas", "Dif (2)"]], use_container_width=True)
