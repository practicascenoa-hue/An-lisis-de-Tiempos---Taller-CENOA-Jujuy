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
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; }
    .sidebar-footer { position: fixed; bottom: 20px; width: 260px; font-size: 11px; color: #666; padding: 10px; border-top: 1px solid #ddd; }
    h1, h2 { color: #002366; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
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
    # Limpieza inicial
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce')
    df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
    df['Etapas'] = df['Etapas'].astype(str).str.strip()
    # Asegurar que Fecha sea datetime para filtrar meses
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    return df

# 3. PROCESAMIENTO
try:
    df_raw = load_data()
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()

    # 4. SIDEBAR
    with st.sidebar:
        st.title("Taller CENOA")
        st.divider()
        opcion = st.radio(
            "Navegación:",
            ["🏠 Inicio", "📈 Análisis tipo de DAÑOS", "👨‍🔧 Productividad de Operarios"],
            label_visibility="collapsed"
        )
        st.markdown("""<div class="sidebar-footer"><b>Taller de Chapa y Pintura CENOA Jujuy</b><br>Las Lomas 2227 – Y4600<br>San Salvador de Jujuy</div>""", unsafe_allow_html=True)

    # 5. CONTENIDO
    if opcion == "🏠 Inicio":
        st.title("Análisis de tiempo - Taller CENOA Jujuy")
        st.write("---")
        ordenes_analizadas = df[df['PAÑOS'].notna() & (df['PAÑOS'] > 0)]['Ref.OR'].nunique()
        c1, c2 = st.columns(2)
        c1.metric("Total de orden analizada", ordenes_analizadas)
        c2.metric("Operarios de planta", 12)

    elif opcion == "📈 Análisis tipo de DAÑOS":
        st.title("📈 Análisis tipo de DAÑOS")
        
        # 1. Listado de Meses
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_sel = st.selectbox("Seleccione el mes a analizar:", meses)
        
        # Mapeo de mes (Enero = 1)
        mes_num = meses.index(mes_sel) + 1
        df_mes = df[df['Fecha'].dt.month == mes_num]
        
        # 2. Selección de Daño con Botones
        st.write("### Seleccione Tipo de Daño:")
        col_a, col_b, col_c = st.columns(3)
        
        # Usamos session_state para guardar la elección del botón
        if 'tipo_sel' not in st.session_state: st.session_state.tipo_sel = 'A'
        
        if col_a.button("DAÑO A"): st.session_state.tipo_sel = 'A'
        if col_b.button("DAÑO B"): st.session_state.tipo_sel = 'B'
        if col_c.button("DAÑO C"): st.session_state.tipo_sel = 'C'
        
        tipo = st.session_state.tipo_sel
        st.info(f"Visualizando: **DAÑO {tipo}** para el mes de **{mes_sel}**")

        # 3. Filtrado por Tipo de Daño (eliminando vacíos)
        df_final = df_mes[df_mes['Tipo de Daño'].astype(str).str.contains(tipo, na=False)]
        
        if not df_final.empty:
            # Agrupación por Actividad (Etapas)
            resumen_actividades = df_final.groupby('Etapas')['Dif (2)'].mean().reset_index()
            resumen_actividades = resumen_actividades.sort_values(by='Dif (2)', ascending=False)
            
            # Aplicar formato H:M para etiquetas del gráfico
            resumen_actividades['Tiempo Formateado'] = resumen_actividades['Dif (2)'].apply(format_hours)
            
            # Gráfico de barras
            fig = px.bar(
                resumen_actividades, 
                x='Dif (2)', 
                y='Etapas', 
                orientation='h',
                text='Tiempo Formateado',
                title=f"Promedio de tiempo por Actividad - Daño {tipo}",
                labels={'Dif (2)': 'Horas Decimales', 'Etapas': 'Actividad'},
                color_discrete_sequence=['#002366']
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=800)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla de respaldo
            st.write("#### Detalle de tiempos")
            st.dataframe(resumen_actividades[['Etapas', 'Tiempo Formateado']].rename(columns={'Tiempo Formateado': 'Promedio (H:M)'}), use_container_width=True)
        else:
            st.warning(f"No hay registros de Daño {tipo} para el mes de {mes_sel}.")

    elif opcion == "👨‍🔧 Productividad de Operarios":
        st.title("👨‍🔧 Ranking de Productividad")
        # (Se mantiene la lógica anterior del ranking)
        etapa_sel = st.selectbox("Etapa a Auditar:", ["Pintado", "Chapa", "Desarme", "Armado", "Pulido"])
        mask_etapa = df['Etapas'].str.contains(etapa_sel.lower(), case=False, na=False)
        df_op = df[mask_etapa].groupby('Operario')['Dif (2)'].mean().reset_index()
        if not df_op.empty:
            avg_ref = df_op['Dif (2)'].mean()
            df_op['Desempeño'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > avg_ref else "✅ Eficiente")
            df_op['Tiempo Promedio'] = df_op['Dif (2)'].apply(format_hours)
            st.table(df_op[['Operario', 'Tiempo Promedio', 'Desempeño']].sort_values(by='Desempeño'))
        else:
            st.info("Sin registros.")

except Exception as e:
    st.error(f"Error: {e}")
