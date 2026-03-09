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

# Estilo corporativo
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .sidebar-footer { position: fixed; bottom: 20px; width: 260px; font-size: 11px; color: #666; padding: 10px; border-top: 1px solid #ddd; }
    h1, h2 { color: #002366; font-family: 'Segoe UI', sans-serif; }
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
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Tipo%20de%20Daños%20(A,B,C)"
    response = requests.get(csv_url)
    df = pd.read_csv(io.StringIO(response.text))
    # Limpieza técnica
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce') # Dejamos NaNs para poder filtrar
    df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
    df['Patente'] = df['Patente'].astype(str).str.upper().str.strip()
    return df

# 3. PROCESAMIENTO
try:
    df_raw = load_data()
    # Filtro de personal técnico (excluyendo administrativos)
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()

    # 4. SIDEBAR
    with st.sidebar:
        st.title("Taller CENOA")
        st.subheader("Gestión de Calidad")
        st.divider()
        
        opcion = st.radio(
            "Navegación:",
            ["🏠 Inicio", "📈 Eficiencia por Daño", "👨‍🔧 Productividad de Operarios"],
            label_visibility="collapsed"
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
        
        # Cálculo de Órdenes Analizadas (Filtro por columna PAÑOS con datos)
        ordenes_con_panos = df[df['PAÑOS'].notna() & (df['PAÑOS'] > 0)]['Ref.OR'].nunique()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total de orden analizada", value=ordenes_con_panos)
        with col2:
            st.metric(label="Operarios de planta", value=12)

    elif opcion == "📈 Eficiencia por Daño":
        st.title("📈 Semáforo de Eficiencia por Etapa")
        tipo_dano = st.selectbox("Seleccione Tipo de Daño:", ["A", "B", "C"])
        
        df_tipo = df[df['Tipo de Daño'].astype(str).str.contains(tipo_dano, na=False)]
        keywords = ["desarme", "chapa", "preparado", "primer", "colorimetria", "pintado", "armado", "pulido", "lavado"]
        
        stats = []
        for k in keywords:
            mask = df_tipo['Etapas'].str.contains(k, case=False, na=False)
            avg = df_tipo.loc[mask, 'Dif (2)'].mean() if any(mask) else 0
            stats.append({'Etapa': k.capitalize(), 'Tiempo': avg})
        
        df_stats = pd.DataFrame(stats)
        obj_global = df_stats[df_stats['Tiempo'] > 0]['Tiempo'].mean()
        df_stats['Color'] = df_stats['Tiempo'].apply(lambda x: '#ef553b' if x > obj_global else '#00cc96')
        
        fig = px.bar(df_stats, x='Etapa', y='Tiempo', color='Color', color_discrete_map="identity",
                     title=f"Eficiencia por Etapa vs Objetivo ({format_hours(obj_global)})")
        fig.add_hline(y=obj_global, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)

    elif opcion == "👨‍🔧 Productividad de Operarios":
        st.title("👨‍🔧 Ranking de Productividad")
        etapa_sel = st.selectbox("Etapa a Auditar:", ["Pintado", "Chapa", "Desarme", "Armado", "Pulido"])
        
        mask_etapa = df['Etapas'].str.contains(etapa_sel.lower(), case=False, na=False)
        df_op = df[mask_etapa].groupby('Operario')['Dif (2)'].mean().reset_index()
        
        if not df_op.empty:
            avg_ref = df_op['Dif (2)'].mean()
            df_op['Desempeño'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > avg_ref else "✅ Eficiente")
            df_op['Tiempo Promedio'] = df_op['Dif (2)'].apply(format_hours)
            
            st.table(df_op[['Operario', 'Tiempo Promedio', 'Desempeño']].sort_values(by='Desempeño'))
            
            st.divider()
            st.subheader(f"🚗 Patentes con demora crítica en {etapa_sel}")
            lentos = df[mask_etapa & (df['Dif (2)'] > avg_ref)].sort_values(by='Dif (2)', ascending=False)
            lentos['Duración'] = lentos['Dif (2)'].apply(format_hours)
            st.dataframe(lentos[['Patente', 'Operario', 'Duración']], use_container_width=True)
        else:
            st.info("No se encontraron registros.")

except Exception as e:
    st.error(f"Error: {e}")
