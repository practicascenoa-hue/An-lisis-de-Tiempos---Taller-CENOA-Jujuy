import streamlit as st
import pandas as pd
import io
import requests

st.set_page_config(page_title="Autolux - Análisis de Tiempos", layout="wide")

st.title("🛠️ Análisis de Tiempos Técnicos por Daño")

# Función para convertir decimal a formato H:M
def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0:
        return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    # Ajuste por si el redondeo de minutos llega a 60
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours}h {minutes:02d}m"

@st.cache_data
def load_data():
    sheet_name = "Tipo%20de%20Daños%20(A,B,C)"
    csv_url = f"https://docs.google.com/spreadsheets/d/1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    response = requests.get(csv_url)
    return pd.read_csv(io.StringIO(response.text))

try:
    df = load_data()

    # 1. Limpieza y Filtros
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['Etapas'] = df['Etapas'].astype(str).str.strip()
    df['Operario'] = df['Operario'].astype(str).str.upper()

    # Excluir Operarios (Basado en historial de Autolux)
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df[~df['Operario'].isin(excluir_ops)]

    # Excluir Etapas administrativas
    excluir_etapas = ["Recepcion", "Control de calidad", "Entrega"]
    for e in excluir_etapas:
        df = df[~df['Etapas'].str.contains(e, case=False, na=False)]

    # 2. Selección de Daño
    tipo_dano = st.selectbox("Seleccione el Tipo de Daño:", ["A", "B", "C"])
    df_filtrado = df[df['Tipo de Daño'].astype(str).str.contains(tipo_dano, na=False)]

    # 3. Flujograma Técnico con conversión a Horas/Minutos
    keywords = [
        "desarme", "chapa", "preparado", "primer", 
        "colorimetria", "pintado", "armado", "pulido", "lavado"
    ]

    st.subheader(f"Promedios del Proceso Técnico - Daño {tipo_dano}")
    cols = st.columns(len(keywords))

    for i, key in enumerate(keywords):
        with cols[i]:
            mask = df_filtrado['Etapas'].str.contains(key, case=False, na=False)
            promedio_decimal = df_filtrado.loc[mask, 'Dif (2)'].mean()
            
            label = key.capitalize()
            # Aplicamos la nueva función de formato
            tiempo_formateado = format_hours(promedio_decimal)
            
            st.metric(label=label, value=tiempo_formateado)
            if i < len(keywords) - 1: st.write("➡️")

    # 4. Tabla Detallada con ambas visualizaciones
    st.divider()
    st.subheader("Desglose de Variantes de Etapas")
    
    tabla_detallada = df_filtrado.groupby('Etapas')['Dif (2)'].agg(['mean', 'count']).reset_index()
    tabla_detallada.columns = ['Etapa detectada en Excel', 'Promedio Decimal', 'Cantidad Autos']
    
    # Añadimos la columna de tiempo amigable a la tabla
    tabla_detallada['Tiempo (H:M)'] = tabla_detallada['Promedio Decimal'].apply(format_hours)
    
    st.dataframe(tabla_detallada[['Etapa detectada en Excel', 'Tiempo (H:M)', 'Cantidad Autos']], use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
