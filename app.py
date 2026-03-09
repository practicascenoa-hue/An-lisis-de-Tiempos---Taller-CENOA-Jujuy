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

# Estilo corporativo y diseño de botones
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .sidebar-footer { position: fixed; bottom: 20px; width: 260px; font-size: 11px; color: #666; padding: 10px; border-top: 1px solid #ddd; }
    h1, h2 { color: #002366; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="column"] > button {
        width: 100%;
        height: 50px;
        font-weight: bold;
        border-radius: 8px;
        background-color: #ffffff;
        border: 2px solid #002366;
        color: #002366;
    }
    div[data-testid="column"] > button:hover {
        background-color: #002366;
        color: #ffffff;
    }
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
    df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce')
    df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
    df['Etapas'] = df['Etapas'].astype(str).str.strip()
    return df

# 3. PROCESAMIENTO
try:
    df_raw = load_data()
    # Filtro de personal técnico
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()

    # 4. SIDEBAR (MENÚ LATERAL)
    with st.sidebar:
        st.title("Taller CENOA")
        st.subheader("Gestión de Calidad")
        st.divider()
        
        opcion = st.radio(
            "Navegación:",
            ["🏠 Inicio", "📈 Análisis tipo de DAÑOS", "👨‍🔧 Productividad de Operarios"],
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
    
    # --- INICIO ---
    if opcion == "🏠 Inicio":
        st.title("Análisis de tiempo - Taller CENOA Jujuy")
        st.write("---")
        st.subheader("Indicadores Generales del Mes")
        
        ordenes_con_panos = df[df['PAÑOS'].notna() & (df['PAÑOS'] > 0)]['Ref.OR'].nunique()
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total de orden analizada", value=ordenes_con_panos)
        with col2:
            st.metric(label="Operarios de planta", value=12)

    # --- ANÁLISIS TIPO DE DAÑOS ---
    elif opcion == "📈 Análisis tipo de DAÑOS":
        st.title("📈 Análisis tipo de DAÑOS")
        
        # 1. Selector de Meses
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_sel = st.selectbox("Seleccione el mes a analizar:", meses)
        
        # Como el Excel es solo de Enero, forzamos la lógica:
        if mes_sel == "Enero":
            df_mes = df.copy()
        else:
            # Si elige otro mes, creamos un dataframe vacío con las mismas columnas
            df_mes = pd.DataFrame(columns=df.columns)
            
        st.divider()
        st.write("### Seleccione Tipo de Daño:")
        
        # 2. Botones de Selección (Guardando estado)
        if 'tipo_dano' not in st.session_state:
            st.session_state.tipo_dano = 'A' # Daño A por defecto
            
        col_a, col_b, col_c = st.columns(3)
        if col_a.button("DAÑO A"): st.session_state.tipo_dano = 'A'
        if col_b.button("DAÑO B"): st.session_state.tipo_dano = 'B'
        if col_c.button("DAÑO C"): st.session_state.tipo_dano = 'C'
        
        tipo_actual = st.session_state.tipo_dano
        st.info(f"Visualizando: **DAÑO {tipo_actual}** | Mes: **{mes_sel}**")

        # 3. Filtrado y Gráfico
        if not df_mes.empty:
            # Filtramos solo el daño seleccionado y eliminamos los que no tengan etapa designada
            df_final = df_mes[
                (df_mes['Tipo de Daño'].astype(str).str.contains(tipo_actual, na=False)) & 
                (df_mes['Etapas'] != 'nan') & 
                (df_mes['Etapas'] != '')
            ]
            
            if not df_final.empty:
                # Agrupamos por Actividad (Etapas) y calculamos el promedio de tiempo
                resumen = df_final.groupby('Etapas')['Dif (2)'].mean().reset_index()
                resumen = resumen.sort_values(by='Dif (2)', ascending=True) # Ascendente para que el gráfico horizontal lo muestre de mayor a menor
                
                # Aplicamos la función para que se lea en Horas y Minutos
                resumen['Tiempo (H:M)'] = resumen['Dif (2)'].apply(format_hours)
                
                # Gráfico de Barras Horizontales
                fig = px.bar(
                    resumen, 
                    x='Dif (2)', 
                    y='Etapas', 
                    orientation='h',
                    text='Tiempo (H:M)', # Muestra las horas formateadas en la barra
                    title=f"Promedio de Tiempos por Actividad - Daño {tipo_actual}",
                    labels={'Dif (2)': 'Horas (Decimal)', 'Etapas': 'Actividades'},
                    height=max(400, len(resumen) * 35) # Ajusta el alto automáticamente según cantidad de actividades
                )
                
                # Diseño del gráfico
                fig.update_traces(textposition='outside', marker_color='#002366')
                fig.update_layout(xaxis_title="Tiempo Promedio", yaxis_title="")
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No hay registros de actividades para el Daño {tipo_actual} en {mes_sel}.")
        else:
            st.warning(f"No hay registros cargados para el mes de {mes_sel}.")


    # --- PRODUCTIVIDAD DE OPERARIOS ---
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
