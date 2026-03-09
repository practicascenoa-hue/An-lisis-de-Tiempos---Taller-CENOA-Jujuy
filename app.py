import streamlit as st
import pandas as pd
import io
import requests

st.set_page_config(page_title="Autolux - Análisis de Tiempos", layout="wide")

st.title("📊 Análisis de Tiempos por Tipo de Daño")

# Función para cargar datos vía CSV directo (más estable)
@st.cache_data
def load_data():
    # Tu ID de hoja: 1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8
    # Nombre de la hoja: Tipo de Daños (A,B,C)
    # El nombre de la hoja en la URL debe ir con codificación para espacios (%20)
    sheet_name = "Tipo%20de%20Daños%20(A,B,C)"
    csv_url = f"https://docs.google.com/spreadsheets/d/1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    
    response = requests.get(csv_url)
    df = pd.read_csv(io.StringIO(response.text))
    return df

try:
    df = load_data()

    # Limpieza de datos: Convertimos 'Dif (2)' a número y limpiamos espacios en 'Etapas'
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['Etapas'] = df['Etapas'].astype(str).str.strip().str.lower()
    df['Tipo de Daño'] = df['Tipo de Daño'].astype(str).str.strip().str.upper()

    # Menú de Selección
    tipo_dano = st.selectbox("Seleccione el Tipo de Daño:", ["A", "B", "C"])
    df_filtrado = df[df['Tipo de Daño'] == tipo_dano]

    st.subheader(f"Flujo de Operación - Daño Tipo {tipo_dano}")

    # Lista oficial de etapas (en minúsculas para coincidir con la limpieza)
    flujograma = [
        "recepcion", "desarme", "chapa", "preparado", "aplicacion de primer",
        "colorimetria", "pintado", "armado", "pulido", "lavado", 
        "control de calidad", "entrega"
    ]

    # Mostrar métricas en columnas
    cols = st.columns(len(flujograma))

    for i, etapa in enumerate(flujograma):
        with cols[i]:
            # Buscamos la etapa
            mask = df_filtrado['Etapas'].str.contains(etapa, na=False)
            promedio = df_filtrado.loc[mask, 'Dif (2)'].mean()
            
            val_display = f"{promedio:.2f} h" if pd.notnull(promedio) and promedio > 0 else "0.00 h"
            
            st.metric(label=etapa.replace(" ", "\n").capitalize(), value=val_display)
            if i < len(flujograma) - 1:
                st.write("➡️")

    # Comparativa de Operarios (Para darte más valor analítico)
    st.divider()
    st.subheader("Eficiencia por Operario (Top 5 más rápidos)")
    op_data = df_filtrado.groupby('Operario')['Dif (2)'].mean().sort_values().head(5)
    st.bar_chart(op_data)

except Exception as e:
    st.error(f"Error cargando los datos: {e}")
    st.info("Asegúrate de que el Google Sheet tenga el acceso compartido para 'Cualquier persona con el enlace'.")
