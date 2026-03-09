import streamlit as st
import pandas as pd
import io
import requests
import plotly.express as px

# 1. CONFIGURACIÓN DE PÁGINA MODO PRO
st.set_page_config(page_title="Taller CENOA Jujuy - Análisis Técnico", layout="wide", page_icon="📈")

# Estilo corporativo avanzado
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    div[data-testid="column"] > button { width: 100%; height: 50px; font-weight: bold; border-radius: 8px; border: 2px solid #002366; color: #002366; transition: all 0.3s; }
    div[data-testid="column"] > button:hover { background-color: #002366; color: #ffffff; transform: scale(1.02); }
    div[data-testid="column"] > button:active { transform: scale(0.98); }
    .sidebar-footer { position: fixed; bottom: 20px; width: 260px; font-size: 11px; color: #666; padding: 10px; border-top: 1px solid #ddd; }
    h1, h2, h3 { color: #002366; font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES DE APOYO Y LIMPIEZA
def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0: return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60: hours += 1; minutes = 0
    return f"{hours}h {minutes:02d}m"

@st.cache_data(ttl=60)
def load_data():
    sheet_id = "1bNgFg5s-1qZuToCInLqCJr4FAUK51m7lrClilBZojb8"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Tipo%20de%20Da%C3%B1os%20(A,B,C)"
    
    try:
        response = requests.get(csv_url)
        if response.status_code != 200: return pd.DataFrame()
        
        df = pd.read_csv(io.StringIO(response.text))
        
        df.columns = df.columns.str.strip()
        if 'Tipo de Daño' not in df.columns:
            cols = [c for c in df.columns if 'daño' in c.lower() or 'dano' in c.lower()]
            if cols: df.rename(columns={cols[0]: 'Tipo de Daño'}, inplace=True)
            
        df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
        df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce')
        df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
        df['Etapas'] = df['Etapas'].astype(str).str.upper().str.strip()
        df['Tipo de Daño'] = df['Tipo de Daño'].astype(str).str.upper().str.strip()
        
        return df
    except Exception:
        return pd.DataFrame()

# Mapeo actualizado de Bloques y Actividades
MAPEO_BLOQUES = {
    "1. RECEPCIÓN": ["RECEPCION"],
    "2. DESARME": ["DESARME", "DESARMADO", "DESARME Y CHAPA", "AYUDA DE DESARME DE CHAPA"],
    "3. CHAPA": ["CHAPA", "MASILLADO Y LIJADO"],
    "4. PREPARADO": ["PREPARADO", "PREPARADO PARAGOLPE", "PREPARADO PARAGOLPE DELANTERO", "PREPARADO CAPERUZA", "PREPARADO DE TAPA DE BAUL", "PREPARACION DE PARAGOLPE", "EMPAPELADO", "LIJADO", "LIJADO PRIMER"],
    "5. APLICACIÓN DE PRIMER": ["APLICACION DE PRIMER"],
    "6. COLORIMETRÍA": ["COLORIMETRIA", "C0LORIMETRIA"],
    "7. PINTADO": ["PINTADO", "PINTAR", "PREPRACION Y PINTADO TEXTURADO PARAGOLPE"],
    "8. ARMADO": ["ARMADO", "REEMPLAZO", "REEMPLAZO DE VIDRIOS", "REEMPLAZO PARABRISAS Y PULIDO", "COLOCACION DE VIDRIO Y PULIDO"],
    "9. PULIDO": ["PULIDO", "PULIDO Y LUSTRADO", "LUSTRADO", "LIJADO Y PULIDO", "LIJADO Y LUSTRADO", "ENCERADO Y PULIDO", "PULIDO PARAGOLPE", "PULIDO GUARDABARRO", "PULIDO Y LASTRE"],
    "10. LAVADO": ["LAVADO", "PULIDO Y LAVADO", "LUSTRADO Y LAVADO", "LIJADO, PULIDO Y LAVADO", "LIJADO, PULIDO Y LUSTRADO DE PIEZAS PINTADA JUNTO CON LAVADO"],
    "11. CONTROL DE CALIDAD": ["CONTROL DE CALIDAD"],
    "12. ENTREGA": ["TERMINACIONES", "LIMPIEZA"]
}

# Función para asignar el bloque a cada etapa
def obtener_bloque(etapa):
    for bloque, sub_etapas in MAPEO_BLOQUES.items():
        if etapa in sub_etapas:
            return bloque
    return "OTRO / NO CLASIFICADO"

# 3. PROCESAMIENTO PRINCIPAL
try:
    df_raw = load_data()
    
    if df_raw.empty:
        st.error("🚨 Error crítico: No se pudieron descargar los datos. Verifica los permisos de acceso al enlace.")
        st.stop()
        
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()
    
    # Asignar el bloque a cada fila
    df['Bloque'] = df['Etapas'].apply(obtener_bloque)

    # 4. SIDEBAR
    with st.sidebar:
        st.title("Taller CENOA")
        opcion = st.radio("Navegación:", ["🏠 Inicio", "📈 Análisis tipo de DAÑOS", "👨‍🔧 Productividad de Operarios"], label_visibility="collapsed")
        st.markdown("""<div class="sidebar-footer"><b>Taller de Chapa y Pintura CENOA Jujuy</b><br>Las Lomas 2227<br>San Salvador de Jujuy</div>""", unsafe_allow_html=True)

    # 5. SUBMENÚS
    if opcion == "🏠 Inicio":
        st.title("Análisis de tiempo - Taller CENOA Jujuy")
        st.divider()
        ordenes = df[df['PAÑOS'].notna() & (df['PAÑOS'] > 0)]['Ref.OR'].nunique()
        c1, c2 = st.columns(2)
        c1.metric("Total de orden analizada", ordenes)
        c2.metric("Operarios de planta", 12)

    elif opcion == "📈 Análisis tipo de DAÑOS":
        st.title("📈 Análisis tipo de DAÑOS")
        mes_sel = st.selectbox("Seleccione el mes a analizar:", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        
        if mes_sel == "Enero":
            st.write("### Seleccione Tipo de Daño:")
            col_a, col_b, col_c = st.columns(3)
            if 'tipo_dano' not in st.session_state: st.session_state.tipo_dano = 'A'
            
            if col_a.button("DAÑO A"): st.session_state.tipo_dano = 'A'
            if col_b.button("DAÑO B"): st.session_state.tipo_dano = 'B'
            if col_c.button("DAÑO C"): st.session_state.tipo_dano = 'C'
            
            tipo = st.session_state.tipo_dano
            
            # Filtro por tipo de daño y quitar los no clasificados si lo deseas
            df_final = df[(df['Tipo de Daño'].str.contains(tipo, na=False)) & (df['Bloque'] != "OTRO / NO CLASIFICADO")]

            if not df_final.empty:
                # 1. Agrupación a nivel de BLOQUES
                resumen_bloques = df_final.groupby('Bloque')['Dif (2)'].mean().reset_index()
                # Ordenar cronológicamente (aprovechando el número en el nombre del bloque, ej: "1. RECEPCIÓN")
                resumen_bloques['Orden'] = resumen_bloques['Bloque'].str.extract('(\d+)').astype(int)
                resumen_bloques = resumen_bloques.sort_values('Orden')
                
                resumen_bloques['Tiempo (H:M)'] = resumen_bloques['Dif (2)'].apply(format_hours)

                st.subheader(f"Promedio de Tiempos por Fase General - DAÑO {tipo}")
                
                fig = px.bar(
                    resumen_bloques, 
                    x='Bloque', 
                    y='Dif (2)', 
                    text='Tiempo (H:M)',
                    title=f"Duración Promedio por Bloque de Trabajo ({mes_sel})",
                    labels={'Dif (2)': 'Horas (Decimal)', 'Bloque': 'Fases del Taller'},
                    color_discrete_sequence=['#002366']
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(yaxis_title="Promedio en Horas", xaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

                st.divider()

                # 2. Agrupación a nivel de ETAPAS DETALLADAS
                st.subheader(f"Desglose Detallado de Actividades - DAÑO {tipo}")
                st.write("Visualiza el tiempo exacto de cada tarea individual que compone los bloques superiores.")
                
                resumen_detallado = df_final.groupby(['Bloque', 'Etapas'])['Dif (2)'].mean().reset_index()
                
                # Ordenar lógicamente por el bloque y luego de mayor a menor tiempo
                resumen_detallado['Orden'] = resumen_detallado['Bloque'].str.extract('(\d+)').astype(int)
                resumen_detallado = resumen_detallado.sort_values(['Orden', 'Dif (2)'], ascending=[True, False])
                
                resumen_detallado['Tiempo Promedio'] = resumen_detallado['Dif (2)'].apply(format_hours)
                
                # Mostrar la tabla formateada limpiando columnas auxiliares
                tabla_mostrar = resumen_detallado[['Bloque', 'Etapas', 'Tiempo Promedio']].rename(columns={'Etapas': 'Actividad Específica'})
                st.dataframe(tabla_mostrar, use_container_width=True, hide_index=True)

            else:
                st.warning(f"No hay registros del Daño {tipo} clasificados en las fases estándar.")
        else:
            st.info(f"No hay datos cargados para {mes_sel}.")

    elif opcion == "👨‍🔧 Productividad de Operarios":
        st.title("👨‍🔧 Ranking de Productividad")
        etapa_sel = st.selectbox("Fase Técnica a Auditar:", list(MAPEO_BLOQUES.keys()))
        sub_etapas = MAPEO_BLOQUES[etapa_sel]
        
        mask_etapa = df['Etapas'].isin(sub_etapas)
        df_op = df[mask_etapa].groupby('Operario')['Dif (2)'].mean().reset_index()
        
        if not df_op.empty:
            avg_ref = df_op['Dif (2)'].mean()
            df_op['Desempeño'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > avg_ref else "✅ Eficiente")
            df_op['Tiempo Promedio'] = df_op['Dif (2)'].apply(format_hours)
            st.table(df_op[['Operario', 'Tiempo Promedio', 'Desempeño']].sort_values(by='Desempeño'))
        else:
            st.info("Sin registros de operarios para esta fase técnica.")

except Exception as e:
    st.error(f"Error general en el sistema: {e}")
