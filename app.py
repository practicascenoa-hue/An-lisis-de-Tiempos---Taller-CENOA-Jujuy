import streamlit as st
import pandas as pd
import io
import requests

st.set_page_config(page_title="Autolux - Análisis Técnico", layout="wide")

st.title("🛠️ Análisis de Tiempos Técnicos por Daño")

@st.cache_data
def load_data():
    sheet_name = "Tipo%20de%20Daños%20(A,B,C)"
    csv_url = f"https://docs.google.com/spreadsheets/d/1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    response = requests.get(csv_url)
    return pd.read_csv(io.StringIO(response.text))

try:
    df = load_data()

    # 1. Limpieza y Filtros Solicitados
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['Etapas'] = df['Etapas'].astype(str).str.strip()
    df['Operario'] = df['Operario'].astype(str).str.upper()

    # Excluir Operarios específicos
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df[~df['Operario'].isin(excluir_ops)]

    # Excluir Etapas administrativas
    excluir_etapas = ["Recepcion", "Control de calidad", "Entrega"]
    # Filtramos si la etapa contiene alguna de estas palabras
    for e in excluir_etapas:
        df = df[~df['Etapas'].str.contains(e, case=False, na=False)]

    # 2. Selección de Daño
    tipo_dano = st.selectbox("Seleccione el Tipo de Daño:", ["A", "B", "C"])
    df_filtrado = df[df['Tipo de Daño'].astype(str).str.contains(tipo_dano, na=False)]

    # 3. Lógica de Agrupación por Palabras Clave
    # Definimos los núcleos del proceso técnico
    keywords = [
        "desarme", "chapa", "preparado", "primer", 
        "colorimetria", "pintado", "armado", "pulido", "lavado"
    ]

    st.subheader(f"Promedios del Proceso Técnico - Daño {tipo_dano}")
    
    # Creamos columnas para el flujo
    cols = st.columns(len(keywords))

    for i, key in enumerate(keywords):
        with cols[i]:
            # Buscamos cualquier fila que incluya la palabra clave (ej: "preparado de chapa")
            mask = df_filtrado['Etapas'].str.contains(key, case=False, na=False)
            data_etapa = df_filtrado.loc[mask]
            promedio = data_etapa['Dif (2)'].mean()
            
            label = key.capitalize()
            val = f"{promedio:.2f} h" if pd.notnull(promedio) and promedio > 0 else "0.00 h"
            
            st.metric(label=label, value=val)
            if i < len(keywords) - 1: st.write("➡️")

    # 4. Análisis Detallado de TODAS las variantes encontradas
    st.divider()
    st.subheader("Desglose detallado por Variantes de Etapas")
    st.write("A continuación se muestran todas las descripciones encontradas en el Excel y sus tiempos:")
    
    # Agrupamos por el nombre exacto que aparece en el Excel
    tabla_detallada = df_filtrado.groupby('Etapas')['Dif (2)'].agg(['mean', 'count']).rename(
        columns={'mean': 'Tiempo Promedio (h)', 'count': 'Frecuencia (Autos)'}
    ).sort_values(by='Tiempo Promedio (h)', ascending=False)
    
    st.dataframe(tabla_detallada, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
