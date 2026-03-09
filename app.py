import streamlit as st
import pandas as pd
import io
import requests
import plotly.figure_factory as ff
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Taller CENOA Jujuy - Análisis de Tiempos", layout="wide")

# Estilo para botones y métricas
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; }
    div[data-testid="column"] > button { width: 100%; height: 50px; font-weight: bold; border: 2px solid #002366; color: #002366; }
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
    df['Dif (2)'] = pd.to_numeric(df['Dif (2)'], errors='coerce').fillna(0)
    df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce')
    df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
    return df

# Mapeo de Actividades según secuencia solicitada
MAPEO_GANTT = {
    "1. RECEPCIÓN": ["RECEPCION"],
    "2. DESARME": ["DESARME", "DESARME Y CHAPA", "AYUDA DE DESARME DE CHAPA"],
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

# 3. PROCESAMIENTO
try:
    df_raw = load_data()
    # Ignorar operarios administrativos
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()

    # SIDEBAR
    with st.sidebar:
        st.title("Taller CENOA")
        opcion = st.radio("Navegación:", ["🏠 Inicio", "📈 Análisis tipo de DAÑOS", "👨‍🔧 Productividad de Operarios"], label_visibility="collapsed")
        st.markdown("""<div style='font-size:11px; margin-top:20px;'><b>Taller CENOA Jujuy</b><br>Las Lomas 2227<br>San Salvador de Jujuy</div>""", unsafe_allow_html=True)

    if opcion == "🏠 Inicio":
        st.title("Análisis de tiempo - Taller CENOA Jujuy")
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
            df_final = df[df['Tipo de Daño'].astype(str).str.contains(tipo, na=False)]

            if not df_final.empty:
                gantt_data = []
                base_date = datetime(2026, 1, 1, 8, 0) # Fecha ficticia para el Gantt
                
                # Clasificar datos según el mapa de secuencia
                for idx, (label, sub_etapas) in enumerate(MAPEO_GANTT.items()):
                    # Filtrar filas que coincidan con las sub-etapas definidas
                    mask = df_final['Etapas'].str.upper().isin([s.upper() for s in sub_etapas])
                    promedio_h = df_final.loc[mask, 'Dif (2)'].mean()
                    
                    if pd.notnull(promedio_h) and promedio_h > 0:
                        start_time = base_date
                        end_time = start_time + timedelta(hours=promedio_h)
                        
                        gantt_data.append(dict(Task=label, Start=start_time, Finish=end_time, Resource=label))
                        # El siguiente bloque empieza donde termina el anterior
                        base_date = end_time

                if gantt_data:
                    st.subheader(f"Diagrama de Gantt: Flujo de Reparación - Daño {tipo}")
                    fig = ff.create_gantt(gantt_data, index_col='Resource', show_colorbar=True, group_tasks=True, showgrid_x=True)
                    fig.update_layout(xaxis_type='date', xaxis=dict(tickformat="%H:%M"), height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Mostrar tabla de tiempos exacta
                    st.write("#### Promedios por Fase Técnica")
                    resumen_df = pd.DataFrame(gantt_data)
                    resumen_df['Duración'] = resumen_df.apply(lambda x: format_hours((x['Finish'] - x['Start']).total_seconds()/3600), axis=1)
                    st.dataframe(resumen_df[['Task', 'Duración']].rename(columns={'Task': 'Fase'}), use_container_width=True)
                else:
                    st.warning(f"No hay actividades registradas para el Daño {tipo} en la secuencia técnica.")
            else:
                st.warning(f"No hay datos para el Daño {tipo}.")
        else:
            st.info(f"No hay datos cargados para {mes_sel}.")

    elif opcion == "👨‍🔧 Productividad de Operarios":
        st.title("👨‍🔧 Ranking de Productividad")
        etapa_sel = st.selectbox("Fase Técnica:", list(MAPEO_GANTT.keys()))
        sub_etapas = MAPEO_GANTT[etapa_sel]
        mask_etapa = df['Etapas'].str.upper().isin([s.upper() for s in sub_etapas])
        df_op = df[mask_etapa].groupby('Operario')['Dif (2)'].mean().reset_index()
        
        if not df_op.empty:
            avg_ref = df_op['Dif (2)'].mean()
            df_op['Desempeño'] = df_op['Dif (2)'].apply(lambda x: "⚠️ Lento" if x > avg_ref else "✅ Eficiente")
            df_op['Promedio'] = df_op['Dif (2)'].apply(format_hours)
            st.table(df_op[['Operario', 'Promedio', 'Desempeño']].sort_values(by='Desempeño'))
        else:
            st.info("Sin registros para esta fase.")

except Exception as e:
    st.error(f"Error: {e}")
