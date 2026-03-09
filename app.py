import streamlit as st
import pandas as pd
import io
import requests
import plotly.express as px

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Taller CENOA Jujuy - Análisis de Tiempos",
    page_icon="📊",
    layout="wide"
)

# Estilo CSS para mejorar la legibilidad sin imágenes
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .sidebar-footer { position: fixed; bottom: 20px; width: 260px; font-size: 11px; color: #666; padding: 10px; border-top: 1px solid #ddd; }
    h1, h2 { color: #002366; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES DE APOYO
def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0: return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60: hours += 1; minutes = 0
    return f"{hours}h {minutes:02d}m"

@st.cache_data
def load_data():
    sheet_id = "1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8"
    # Nombre de la hoja: Tipo de Daños (A,B,C)
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Tipo%20de%20Daños%20(A,B,C)"
    response = requests.get(csv_url)
    df = pd.read_csv(io.StringIO(response.text))
    # Limpieza de datos
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
    df['Patente'] = df['Patente'].astype(str).str.upper().str.strip()
    return df

# 3. LÓGICA DE DATOS Y FILTROS
try:
    df_raw = load_data()
    # Excluir personal administrativo según perfil de Autolux
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()

    # 4. SIDEBAR (MENÚ LATERAL)
    with st.sidebar:
        st.title("Taller CENOA")
        st.subheader("Gestión de Calidad")
        st.divider()
        
        opcion = st.radio(
            "Seleccione un Análisis:",
            ["🏠 Inicio", "📈 Eficiencia por Daño", "👨‍🔧 Productividad de Operarios"]
        )
        
        st.markdown(
            """
            <div class="sidebar-footer">
                <b>Taller de Chapa y Pintura CENOA Jujuy</b><br>
                Las Lomas 2227 – Y4600<br>
                San Salvador de Jujuy – Provincia de Jujuy
            </div>
            """, 
            unsafe_allow_html=True
        )

    # 5. CONTENIDO DE LOS SUBMENÚS
    if opcion == "🏠 Inicio":
        st.title("Análisis de tiempo - Taller CENOA Jujuy")
        st.write("---")
        st.subheader("Indicadores Generales del Mes")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Órdenes", len(df))
        with col2:
            st.metric("Promedio de Entrega", format_hours(df['Dif (2)'].mean()))
        with col3:
            st.metric("Operarios en Planta", df['Operario'].nunique())

    elif opcion == "📈 Eficiencia por Daño":
        st.title("📈 Semáforo de Eficiencia por Etapa")
        tipo_dano = st.selectbox("Seleccione Tipo de Daño:", ["A", "B", "C"])
        
        # Filtro por tipo de daño
        df_tipo = df[df['Tipo de Daño'].astype(str).str.contains(tipo_dano, na=False)]
        
        # Etapas del flujograma técnico solicitado
        keywords = ["desarme", "chapa", "preparado", "primer", "colorimetria", "pintado", "armado", "pulido", "lavado"]
        stats = []
        for k in keywords:
            mask = df_tipo['Etapas'].str.contains(k, case=False, na=False)
            avg = df_tipo.loc[mask, 'Dif (2)'].mean() if any(mask) else 0
            stats.append({'Etapa': k.capitalize(), 'Tiempo': avg})
        
        df_stats = pd.DataFrame(stats)
        # El Objetivo es el promedio de todas las etapas para este daño
        objetivo_general = df_stats[df_stats['Tiempo'] > 0]['Tiempo'].mean()
        
        # Color del semáforo: Rojo si supera el promedio, Verde si es menor
        df_stats['Color'] = df_stats['Tiempo'].apply(lambda x: '#ef553b' if x > objetivo_general else '#00cc96')
        
        fig = px.bar(df_stats, x='Etapa', y='Tiempo', color='Color', color_discrete_map="identity",
                     title=f"Eficiencia por Etapa vs Objetivo ({format_hours(objetivo_general)})")
        fig.add_hline(y=objetivo_general, line_dash="dash", line_color="black", annotation_text="Promedio Objetivo")
        st.plotly_chart(fig, use_container_width=True)

    elif opcion == "👨‍🔧 Productividad de Operarios":
        st.title("👨‍🔧 Ranking de Productividad")
        etapa_sel = st.selectbox("Seleccione Etapa para Auditar:", ["Pintado", "Chapa", "Desarme", "Armado", "Pulido"])
        
        # Lógica de ranking: comparativa contra el promedio de la etapa
        mask_etapa = df['Etapas'].str.contains(etapa_sel.lower(), case=False, na=False)
        df_op = df[mask_etapa].groupby('Operario')['Dif (2)'].mean().reset_index()
        
        if not df_op.empty:
            avg_ref = df_op['Dif (2)'].mean()
            df_op['Desempeño'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > avg_ref else "✅ Eficiente")
            df_op['Tiempo Promedio'] = df_op['Dif (2)'].apply(format_hours)
            
            st.subheader(f"Comparativa de Técnicos en {etapa_sel}")
            st.table(df_op[['Operario', 'Tiempo Promedio', 'Desempeño']].sort_values(by='Desempeño'))
            
            # Vehículos con mayor demora (Outliers)
            st.divider()
            st.subheader(f"🚗 Patentes con demora crítica en {etapa_sel}")
            lentos = df[mask_etapa & (df['Dif (2)'] > avg_ref)].sort_values(by='Dif (2)', ascending=False)
            lentos['Duración'] = lentos['Dif (2)'].apply(format_hours)
            st.dataframe(lentos[['Patente', 'Operario', 'Duración']], use_container_width=True)
        else:
            st.info("No se encontraron registros para esta etapa con los filtros actuales.")

except Exception as e:
    st.error(f"Error de conexión o datos: {e}")
