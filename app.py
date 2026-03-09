import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Autolux - Análisis de Tiempos", layout="wide")

st.title("📊 Análisis de Tiempos por Tipo de Daño")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    url = "https://docs.google.com/spreadsheets/d/1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8/edit?usp=sharing"
    # Forzamos la lectura de la hoja específica
    df = conn.read(spreadsheet=url, worksheet="Tipo de Daños (A,B,C)")

    # Limpieza de datos
    # Convertimos la columna de tiempo a número, eliminando lo que no sea número
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)

    # Menú
    tipo_dano = st.selectbox("Seleccione el Tipo de Daño:", ["A", "B", "C"])
    df_filtrado = df[df['Tipo de Daño'] == tipo_dano]

    st.subheader(f"Flujo de Operación - Daño Tipo {tipo_dano}")

    # Lista oficial de etapas
    flujograma = [
        "Recepcion", "desarme", "chapa", "preparado", "aplicacion de primer",
        "colorimetria", "pintado", "armado", "pulido", "lavado", 
        "control de calidad", "entrega"
    ]

    # Mostrar métricas
    cols = st.columns(len(flujograma))

    for i, etapa in enumerate(flujograma):
        with cols[i]:
            # Buscamos filas que CONTENGAN el nombre de la etapa (ignorando mayúsculas)
            mask = df_filtrado['Etapas'].str.contains(etapa, case=False, na=False)
            promedio = df_filtrado.loc[mask, 'Dif (2)'].mean()
            
            # Si el promedio es NaN (no hay datos), mostramos 0
            val_display = f"{promedio:.2f} h" if pd.notnull(promedio) else "N/A"
            
            st.metric(label=etapa.capitalize(), value=val_display)
            if i < len(flujograma) - 1:
                st.write("➡️")

except Exception as e:
    st.error(f"Error de conexión: {e}")
