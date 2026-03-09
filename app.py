import streamlit as st
import pandas as pd
import io
import requests
import plotly.express as px
import base64

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Taller CENOA Jujuy - Análisis de Tiempos",
    page_icon="📊",
    layout="wide"
)

# 2. FUNCIONES DE APOYO (Imagen de fondo y Formato)
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0: return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60: hours += 1; minutes = 0
    return f"{hours}h {minutes:02d}m"

# Inyectar CSS para Fondo y Estilo
fondo_base64 = get_base64_of_bin_file('fondo-taller.jpeg')
if fondo_base64:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(255,255,255,0.9), rgba(255,255,255,0.9)), url("data:image/jpeg;base64,{fondo_base64}");
            background-size: cover;
            background-attachment: fixed;
        }}
        [data-testid="stMetricValue"] {{ font-size: 1.8rem !important; }}
        </style>
        """,
        unsafe_allow_html=True
    )

# 3. CARGA DE DATOS
@st.cache_data
def load_data():
    sheet_id = "1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Tipo%20de%20Daños%20(A,B,C)"
    response = requests.get(csv_url)
    df = pd.read_csv(io.StringIO(response.text))
    # Limpieza
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
    return df

try:
    df_full = load_data()
    # Excluir administrativos
    excluir = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_full[~df_full['Operario'].isin(excluir)].copy()

    # 4. MENÚ LATERAL (SIDEBAR)
    with st.sidebar:
        try:
            st.image("logo-taller-cenoa.png", use_container_width=True)
        except:
            st.title("Taller CENOA")
        
        st.divider()
        opcion = st.radio(
            "Navegación:",
            ["🏠 Inicio", "📈 Eficiencia por Daño", "👨‍🔧 Productividad de Operarios"]
        )
        st.divider()
        st.info("San Salvador de Jujuy, Argentina")

    # 5. CONTENIDO DE SUBMENÚS
    if opcion == "🏠 Inicio":
        st.title("Análisis de tiempo - Taller CENOA Jujuy")
        st.subheader("Bienvenido al Portal de Auditoría de Postventa")
        st.write("Seleccione un análisis técnico en el menú lateral para visualizar los indicadores de eficiencia.")
        
        # Resumen rápido en Inicio
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Reparaciones", len(df))
        c2.metric("Promedio General", format_hours(df['Dif (2)'].mean()))
        c3.metric("Operarios Activos", df['Operario'].nunique())

    elif opcion == "📈 Eficiencia por Daño":
        st.header("📈 Semáforo de Eficiencia por Etapa")
        tipo = st.selectbox("Tipo de Daño:", ["A", "B", "C"])
        df_tipo = df[df['Tipo de Daño'].astype(str).str.contains(tipo, na=False)]
        
        keywords = ["desarme", "chapa", "preparado", "primer", "colorimetria", "pintado", "armado", "pulido", "lavado"]
        stats = []
        for k in keywords:
            m = df_tipo['Etapas'].str.contains(k, case=False, na=False)
            avg = df_tipo.loc[m, 'Dif (2)'].mean() if any(m) else 0
            stats.append({'Etapa': k.capitalize(), 'Tiempo': avg})
        
        df_stats = pd.DataFrame(stats)
        obj = df_stats[df_stats['Tiempo'] > 0]['Tiempo'].mean()
        df_stats['Color'] = df_stats['Tiempo'].apply(lambda x: '#ef553b' if x > obj else '#00cc96')
        
        fig = px.bar(df_stats, x='Etapa', y='Tiempo', color='Color', color_discrete_map="identity",
                     title=f"Eficiencia Daño {tipo} vs Objetivo ({format_hours(obj)})")
        fig.add_hline(y=obj, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)

    elif opcion == "👨‍🔧 Productividad de Operarios":
        st.header("👨‍🔧 Ranking y Patentes Críticas")
        etapa_sel = st.selectbox("Seleccione Etapa:", ["Pintado", "Chapa", "Desarme", "Armado", "Pulido"])
        
        mask_etapa = df['Etapas'].str.contains(etapa_sel.lower(), case=False, na=False)
        df_op = df[mask_etapa].groupby('Operario')['Dif (2)'].mean().reset_index()
        
        if not df_op.empty:
            avg_ref = df_op['Dif (2)'].mean()
            df_op['Estado'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > avg_ref else "✅ Eficiente")
            df_op['Tiempo'] = df_op['Dif (2)'].apply(format_hours)
            
            st.subheader(f"Desempeño en {etapa_sel}")
            st.table(df_op[['Operario', 'Tiempo', 'Estado']].sort_values(by='Estado'))
            
            st.subheader("🚗 Patentes con mayor demora")
            lentos = df[mask_etapa & (df['Dif (2)'] > avg_ref)].sort_values(by='Dif (2)', ascending=False)
            lentos['H:M'] = lentos['Dif (2)'].apply(format_hours)
            st.dataframe(lentos[['Patente', 'Operario', 'H:M']], use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
