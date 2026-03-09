import streamlit as st
import pandas as pd
import io
import requests
import plotly.express as px
import plotly.graph_objects as ob

# Configuración Profesional
st.set_page_config(page_title="Taller CENOA Jujuy - Auditoría de Tiempos", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Taller CENOA Jujuy - Panel de Control de Eficiencia")

def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0: return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60: hours += 1; minutes = 0
    return f"{hours}h {minutes:02d}m"

@st.cache_data
def load_data():
    sheet_name = "Tipo%20de%20Daños%20(A,B,C)"
    csv_url = f"https://docs.google.com/spreadsheets/d/1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8/gviz/tq?tqx=out:csv&sheet={sheet_name}"
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

    # --- 1. SEMÁFORO DE EFICIENCIA PROFESIONAL ---
    st.subheader(f"📈 Análisis de Tiempos Críticos - Daño {tipo_dano}")
    
    keywords = ["desarme", "chapa", "preparado", "primer", "colorimetria", "pintado", "armado", "pulido", "lavado"]
    stats = []

    for key in keywords:
        mask = df_filtrado['Etapas'].str.contains(key, case=False, na=False)
        promedio_actual = df_filtrado.loc[mask, 'Dif (2)'].mean() if any(mask) else 0
        # El objetivo es el promedio general para ese tipo de daño
        stats.append({'Etapa': key.capitalize(), 'Tiempo': promedio_actual})

    df_stats = pd.DataFrame(stats)
    promedio_global_dano = df_stats['Tiempo'].mean()

    # Gráfico de Barras con Semáforo
    df_stats['Color'] = df_stats['Tiempo'].apply(lambda x: '#ef553b' if x > promedio_global_dano else '#00cc96')
    
    fig_semaforo = px.bar(df_stats, x='Etapa', y='Tiempo', text_auto='.2f',
                          title=f"Eficiencia por Etapa (Línea = Promedio General {tipo_dano})",
                          color='Color', color_discrete_map="identity")
    fig_semaforo.add_hline(y=promedio_global_dano, line_dash="dash", line_color="black", annotation_text="Objetivo (Promedio)")
    st.plotly_chart(fig_semaforo, use_container_width=True)

    # --- 2. RANKING DE PRODUCTIVIDAD Y DESVÍOS ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👨‍🔧 Desempeño por Operario")
        etapa_sel = st.selectbox("Filtrar por Etapa:", [k.capitalize() for k in keywords])
        
        mask_op = df_filtrado['Etapas'].str.contains(etapa_sel.lower(), case=False, na=False)
        df_op = df_filtrado[mask_op].groupby('Operario')['Dif (2)'].mean().reset_index()
        
        if not df_op.empty:
            prom_ref = df_stats[df_stats['Etapa'] == etapa_sel]['Tiempo'].values[0]
            df_op['Estatus'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > prom_ref else "✅ Eficiente")
            
            fig_op = px.scatter(df_op, x='Operario', y='Dif (2)', color='Estatus',
                                size='Dif (2)', title=f"Operarios en {etapa_sel}",
                                color_discrete_map={"⚠️ Lento": "#ef553b", "✅ Eficiente": "#00cc96"})
            st.plotly_chart(fig_op, use_container_width=True)
        else:
            st.info("Sin datos para esta etapa.")

    with col2:
        st.subheader("🚗 Vehículos con mayor demora (Outliers)")
        # Identificar patentes que superaron el promedio de su etapa
        df_outliers = df_filtrado.copy()
        
        def es_lento(row):
            for k in keywords:
                if k in str(row['Etapas']).lower():
                    ref = df_stats[df_stats['Etapa'] == k.capitalize()]['Tiempo'].values[0]
                    return row['Dif (2)'] > ref
            return False

        df_outliers['Es_Lento'] = df_outliers.apply(es_lento, axis=1)
        tabla_patentes = df_outliers[df_outliers['Es_Lento']].sort_values(by='Dif (2)', ascending=False)

        if not tabla_patentes.empty:
            st.write("Vehículos que excedieron el tiempo promedio:")
            st.dataframe(tabla_patentes[['Patente', 'Etapas', 'Operario', 'Dif (2)']].rename(
                columns={'Dif (2)': 'Horas'}), use_container_width=True)
        else:
            st.success("No hay vehículos con demoras críticas detectadas.")

except Exception as e:
    st.error(f"Error en el sistema: {e}")
