import streamlit as st
import pandas as pd
import io
import requests

# Configuración con el nombre correcto de la sucursal
st.set_page_config(page_title="Taller CENOA Jujuy - Análisis de Tiempos", layout="wide")

st.title("🛠️ Taller CENOA Jujuy - Panel de Eficiencia Técnica")

def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0:
        return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
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
    df_raw = load_data()

    # --- 1. LIMPIEZA Y FILTROS INICIALES ---
    df_raw['Dif (2)'] = pd.to_numeric(df_raw['Dif (2)'], errors='coerce').fillna(0)
    df_raw['PAÑOS'] = pd.to_numeric(df_raw['PAÑOS'], errors='coerce').fillna(0)
    df_raw['Operario'] = df_raw['Operario'].astype(str).str.upper().str.strip()
    
    # Exclusión de personal administrativo
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()

    # --- 2. BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros de Análisis")
    
    tipo_dano = st.sidebar.selectbox("Tipo de Daño:", ["A", "B", "C"])
    
    # Filtro por Cantidad de Paños
    min_panos = int(df['PAÑOS'].min())
    max_panos = int(df['PAÑOS'].max())
    rango_panos = st.sidebar.slider("Rango de Paños:", min_panos, max_panos, (min_panos, max_panos))

    # Aplicar Filtros
    df_filtrado = df[
        (df['Tipo de Daño'].astype(str).str.contains(tipo_dano, na=False)) &
        (df['PAÑOS'] >= rango_panos[0]) &
        (df['PAÑOS'] <= rango_panos[1])
    ]

    # --- 3. SEMÁFORO DE EFICIENCIA (KPIs) ---
    keywords = ["desarme", "chapa", "preparado", "primer", "colorimetria", "pintado", "armado", "pulido", "lavado"]
    
    st.subheader(f"Flujo de Operación - Daño {tipo_dano} ({rango_panos[0]} a {rango_panos[1]} paños)")
    cols = st.columns(len(keywords))

    # Guardaremos los promedios para el ranking posterior
    dict_promedios = {}

    for i, key in enumerate(keywords):
        with cols[i]:
            mask = df_filtrado['Etapas'].str.contains(key, case=False, na=False)
            data_etapa = df_filtrado.loc[mask]
            promedio_actual = data_etapa['Dif (2)'].mean() if not data_etapa.empty else 0
            dict_promedios[key] = promedio_actual
            
            # Lógica de Semáforo: Comparamos contra el promedio general del mismo daño (sin filtro de paños)
            promedio_objetivo = df[df['Tipo de Daño'].astype(str).str.contains(tipo_dano, na=False) & 
                                   df['Etapas'].str.contains(key, case=False, na=False)]['Dif (2)'].mean()

            # Determinar color de la métrica (delta)
            # Si el tiempo es menor al objetivo -> Verde (negativo en delta es bueno)
            delta_val = promedio_actual - promedio_objetivo if pd.notnull(promedio_objetivo) else 0
            
            st.metric(
                label=key.capitalize(), 
                value=format_hours(promedio_actual),
                delta=f"{delta_val:.2f}h vs Prom. Gral",
                delta_color="inverse" # Rojo si sube, Verde si baja
            )

    # --- 4. LISTADO DE PRODUCTIVIDAD POR OPERARIO ---
    st.divider()
    st.subheader("Análisis de Operarios por Etapa")
    
    etapa_analisis = st.selectbox("Seleccione etapa para ver operarios sobre el promedio:", [k.capitalize() for k in keywords])
    key_busqueda = etapa_analisis.lower()
    
    # Filtrar operarios que trabajaron en esa etapa
    mask_etapa = df_filtrado['Etapas'].str.contains(key_busqueda, case=False, na=False)
    df_op_etapa = df_filtrado[mask_etapa].groupby('Operario')['Dif (2)'].mean().reset_index()
    
    prom_etapa_ref = dict_promedios.get(key_busqueda, 0)
    
    if not df_op_etapa.empty:
        # Identificar quiénes están por encima del promedio (menos eficientes en tiempo)
        df_op_etapa['Situación'] = df_op_etapa['Dif (2)'].apply(
            lambda x: "⚠️ Por encima del promedio" if x > prom_etapa_ref else "✅ Por debajo del promedio"
        )
        df_op_etapa['Tiempo'] = df_op_etapa['Dif (2)'].apply(format_hours)
        
        st.table(df_op_etapa[['Operario', 'Tiempo', 'Situación']].sort_values(by='Situación'))
    else:
        st.write("No hay datos para esta etapa con los filtros seleccionados.")

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
