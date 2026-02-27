import streamlit as st
import pandas as pd

st.title("Portal Taller CENOA")
st.subheader("Análisis - Tipo de Daños (A,B,C)")

# ID de tu sheet
SHEET_ID = "1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8"

# ⚠️ Reemplazar con el gid correcto de la hoja "Tipo de Daños (A,B,C)"
GID = "0"

url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# Leer datos
df = pd.read_csv(url)

st.write("Vista previa de datos")
st.dataframe(df)

# --- ANALISIS ---

# Suponiendo que la columna se llama "Tipo de Daño"
if "Tipo de Daño" in df.columns:
    
    resumen = df["Tipo de Daño"].value_counts().reset_index()
    resumen.columns = ["Tipo de Daño", "Cantidad"]

    st.subheader("Cantidad por Tipo de Daño")
    st.dataframe(resumen)

    st.bar_chart(resumen.set_index("Tipo de Daño"))

else:
    st.warning("No se encontró la columna 'Tipo de Daño'")

