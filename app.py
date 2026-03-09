import streamlit as st
import pandas as pd
import io
import requests
import plotly.express as px

# Configuración Profesional
st.set_page_config(page_title="Taller CENOA Jujuy - Auditoría de Tiempos", layout="wide")

st.title("📊 Taller CENOA Jujuy - Panel de Control de Eficiencia")

def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0: return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60: hours += 1; minutes = 0
    return f"{hours}h {minutes:02d}m"

@st.cache_data
def load_data():
    # ID del documento y nombre de la hoja corregido para la URL
    sheet_id = "1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8"
    sheet_name = "Tipo de Daños (A,B,C)"
    # Usamos quote para evitar errores de caracteres de control
    import urllib.parse
    safe_name = urllib.parse.quote(sheet_name)
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={safe_name}"
    
    response = requests.get(csv_url)
    return pd.read_csv(io.StringIO(response.text))

try:
    df_raw = load_data()
    
    # Limpieza de datos
    df_raw['Dif (2)'] = pd.to_numeric(df_raw['Dif (2)'], errors='coerce').fillna(0)
    df_raw['Operario'] = df_raw['Operario'].astype(str).str.upper().str.strip()
    df_raw['Patente'] = df_raw['Patente'].astype(str).str.upper().str.strip()
    
    # Excluir personal administrativo
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()

    # Selección de Tipo de Daño
    tipo_dano = st.selectbox("🎯 Seleccione Tipo de Daño para Auditoría:", ["A", "B", "C"])
    df_filtrado = df[df['Tipo de Daño'].astype(str).str.contains(tipo_dano, na=False)]

    # --- SEMÁFORO DE EFICIENCIA PROFESIONAL ---
    st.subheader(f"📈 Análisis de Tiempos Críticos - Daño {tipo_dano}")
    
    keywords = ["desarme", "chapa", "preparado", "primer", "colorimetria", "pintado", "armado", "pulido", "lavado"]
    stats = []

    for key in keywords:
        mask = df_filtrado['Etapas'].str.contains(key, case=False, na=False)
        promedio_etapa = df_filtrado.loc[mask, 'Dif (2)'].mean() if any(mask) else 0
        stats.append({'Etapa': key.capitalize(), 'Tiempo': promedio_etapa})

    df_stats = pd.DataFrame(stats)
    # El objetivo es el promedio general de todas las etapas para este tipo de daño
    objetivo = df_stats[df_stats['Tiempo'] > 0]['Tiempo'].mean()

    # Gráfico de Barras con Semáforo (Verde/Rojo)
    df_stats['Color'] = df_stats['Tiempo'].apply(lambda x: '#ef553b' if x > objetivo else '#00cc96')
    
    fig_semaforo = px.bar(df_stats, x='Etapa', y='Tiempo', text_auto='.2f',
                          title=f"Promedios por Etapa vs Objetivo ({format_hours(objetivo)})",
                          color='Color', color_discrete_map="identity")
    fig_semaforo.add_hline(y=objetivo, line_dash="dash", line_color="black", annotation_text="Promedio General (Objetivo)")
    st.plotly_chart(fig_semaforo, use_container_width=True)

    # --- RANKING DE OPERARIOS Y PATENTES CRÍTICAS ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👨‍🔧 Desempeño por Operario")
        etapa_sel = st.selectbox("Ver operarios en la etapa:", [k.capitalize() for k in keywords])
        
        mask_op = df_filtrado['Etapas'].str.contains(etapa_sel.lower(), case=False, na=False)
        df_op = df_filtrado[mask_op].groupby('Operario')['Dif (2)'].mean().reset_index()
        
        if not df_op.empty:
            ref_etapa = df_stats[df_stats['Etapa'] == etapa_sel]['Tiempo'].values[0]
            df_op['Estatus'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > ref_etapa else "✅ Eficiente")
            df_op['Tiempo Formato'] = df_op['Dif (2)'].apply(format_hours)
            
            st.dataframe(df_op[['Operario', 'Tiempo Formato', 'Estatus']].sort_values(by='Estatus'), use_container_width=True)
        else:
            st.info("Sin datos para esta etapa.")

    with col2:
        st.subheader("🚗 Patentes con mayor demora")
        # Filtrar vehículos que tardaron más del promedio en su etapa
        df_outliers = df_filtrado.copy()
        
        def es_lento(row):
            for k in keywords:
                if k in str(row['Etapas']).lower():
                    ref = df_stats[df_stats['Etapa'] == k.capitalize()]['Tiempo'].values[0]
                    return row['Dif (2)'] > ref
            return False

        df_outliers['Demora_Excesiva'] = df_outliers.apply(es_lento, axis=1)
        patentes_criticas = df_outliers[df_outliers['Demora_Excesiva']].sort_values(by='Dif (2)', ascending=False)

        if not patentes_criticas.empty:
            patentes_criticas['Horas/Min'] = patentes_criticas['Dif (2)'].apply(format_hours)
            st.dataframe(patentes_criticas[['Patente', 'Etapas', 'Operario', 'Horas/Min']], use_container_width=True)
        else:
            st.success("No hay patentes con demoras críticas.")

except Exception as e:
    st.error(f"Error detectado: {e}")
