import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración de página
st.set_page_config(page_title="Análisis de Tiempos", layout="wide")

st.title("📊 Análisis de Tiempos por Tipo de Daño")

# 1. Conexión a Google Sheets
# Nota: Asegúrate de tener 'st-gsheets-connection' en tu requirements.txt
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Cambia la URL por la de tu archivo si es necesario
    url = "https://docs.google.com/spreadsheets/d/1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8/edit?usp=sharing"
    
    # Leemos la hoja específica que mencionaste
    df = conn.read(spreadsheet=url, worksheet="Tipo de Daños (A,B,C)")

    # Limpieza básica: Aseguramos que 'Dif (2)' sea numérico
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)

    # 2. Menú de Selección de Tipo de Daño
    tipos_disponibles = df['Tipo de Daño'].unique() if 'Tipo de Daño' in df.columns else ["A", "B", "C"]
    tipo_dano = st.selectbox("Seleccione el Tipo de Daño para analizar:", tipos_disponibles)

    # Filtrar datos por el tipo seleccionado
    df_filtrado = df[df['Tipo de Daño'] == tipo_dano]

    st.subheader(f"Flujo de Operación - Daño Tipo {tipo_dano}")

    # 3. Definición del Flujograma (Orden Operacional)
    flujograma = [
        "Recepcion", "desarme", "chapa", "preparado", "aplicacion de primer",
        "colorimetria", "pintado", "armado", "pulido", "lavado", 
        "control de calidad", "entrega"
    ]

    # Mostrar métricas en columnas
    cols = st.columns(len(flujograma))

    for i, etapa in enumerate(flujograma):
        with cols[i]:
            # Calculamos el promedio real para esa etapa
            # Filtramos por la columna 'Etapas' del Excel
            valor_etapa = df_filtrado[df_filtrado['Etapas'].str.contains(etapa, case=False, na=False)]
            promedio = valor_etapa['Dif (2)'].mean() if not valor_etapa.empty else 0.0
            
            st.metric(label=etapa.capitalize(), value=f"{promedio:.2f} h")
            if i < len(flujograma) - 1:
                st.write("➡️")

    # 4. Gráfico Comparativo
    st.divider()
    st.subheader("Comparativa Visual de Etapas (Promedios)")
    
    # Preparamos datos para el gráfico
    chart_data = []
    for etapa in flujograma:
        p = df_filtrado[df_filtrado['Etapas'].str.contains(etapa, case=False, na=False)]['Dif (2)'].mean()
        chart_data.append({"Etapa": etapa, "Promedio": p if pd.notnull(p) else 0})
    
    df_chart = pd.DataFrame(chart_data)
    st.bar_chart(df_chart.set_index("Etapa"))

except Exception as e:
    st.error(f"Error al conectar con la hoja: {e}")
    st.info("Asegúrate de que la hoja 'Tipo de Daños (A,B,C)' existe y las columnas coinciden exactamente.")
