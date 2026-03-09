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
        df['Patente'] = df['Patente'].astype(str).str.upper().str.strip() 
        
        return df
    except Exception:
        return pd.DataFrame()

# Mapeo actualizado de Bloques (10 Etapas puramente operativas)
MAPEO_BLOQUES = {
    "1. DESARME": ["DESARME"],
    "2. CHAPA": ["CHAPA", "MASILLADO Y LIJADO"],
    "3. PREPARADO": ["PREPARADO", "PREPARADO PARAGOLPE", "PREPARADO PARAGOLPE DELANTERO", "PREPARADO CAPERUZA", "PREPARADO DE TAPA DE BAUL", "PREPARACION DE PARAGOLPE", "EMPAPELADO", "LIJADO", "LIJADO PRIMER"],
    "4. APLICACIÓN DE PRIMER": ["APLICACION DE PRIMER"],
    "5. COLORIMETRÍA": ["COLORIMETRIA", "C0LORIMETRIA"],
    "6. PINTADO": ["PINTADO", "PINTAR", "PREPRACION Y PINTADO TEXTURADO PARAGOLPE"],
    "7. ARMADO": ["ARMADO", "REEMPLAZO", "REEMPLAZO DE VIDRIOS", "REEMPLAZO PARABRISAS Y PULIDO", "COLOCACION DE VIDRIO Y PULIDO"],
    "8. PULIDO": ["PULIDO", "PULIDO Y LUSTRADO", "LUSTRADO", "LIJADO Y PULIDO", "LIJADO Y LUSTRADO", "ENCERADO Y PULIDO", "PULIDO PARAGOLPE", "PULIDO GUARDABARRO", "PULIDO Y LASTRE"],
    "9. LAVADO": ["LAVADO", "PULIDO Y LAVADO", "LUSTRADO Y LAVADO", "LIJADO, PULIDO Y LAVADO", "LIJADO, PULIDO Y LUSTRADO DE PIEZAS PINTADA JUNTO CON LAVADO"],
    "10. ENTREGA": ["TERMINACIONES", "LIMPIEZA"]
}

def obtener_bloque(etapa):
    for bloque, sub_etapas in MAPEO_BLOQUES.items():
        if etapa in sub_etapas:
            return bloque
    return "OTRO / NO CLASIFICADO"

def limpiar_dano(val):
    val = str(val).upper()
    if 'A' in val: return 'A'
    if 'B' in val: return 'B'
    if 'C' in val: return 'C'
    return None

# 3. PROCESAMIENTO PRINCIPAL
try:
    df_raw = load_data()
    
    if df_raw.empty:
        st.error("🚨 Error crítico: No se pudieron descargar los datos. Verifica los permisos de acceso al enlace.")
        st.stop()
        
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()
    
    df['Bloque'] = df['Etapas'].apply(obtener_bloque)
    df['Tipo Limpio'] = df['Tipo de Daño'].apply(limpiar_dano)

    # 4. SIDEBAR
    with st.sidebar:
        st.title("Taller CENOA")
        opcion = st.radio("Navegación:", ["🏠 Inicio", "📈 Análisis tipo de DAÑOS", "👨‍🔧 Productividad de Operarios"], label_visibility="collapsed")
        st.markdown("""<div class="sidebar-footer"><b>Taller de Chapa y Pintura CENOA Jujuy</b><br>Las Lomas 2227<br>San Salvador de Jujuy</div>""", unsafe_allow_html=True)

    # --------------------------------------------------------------------------------
    # 5. SUBMENÚ: INICIO
    # --------------------------------------------------------------------------------
    if opcion == "🏠 Inicio":
        st.title("Análisis de tiempo - Taller CENOA Jujuy")
        st.divider()
        ordenes = df[df['PAÑOS'].notna() & (df['PAÑOS'] > 0)]['Ref.OR'].nunique()
        c1, c2 = st.columns(2)
        c1.metric("Total de orden analizada", ordenes)
        c2.metric("Operarios de planta", 12)

    # --------------------------------------------------------------------------------
    # 5. SUBMENÚ: ANÁLISIS TIPO DE DAÑOS
    # --------------------------------------------------------------------------------
    elif opcion == "📈 Análisis tipo de DAÑOS":
        st.title("📈 Análisis tipo de DAÑOS")
        mes_sel = st.selectbox("Seleccione el mes a analizar:", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        
        if mes_sel == "Enero":
            st.write("### Seleccione Tipo de Daño:")
            
            df_patentes = df[(df['Patente'] != 'NAN') & (df['Patente'] != '') & (df['Patente'].notna())] 
            cant_a = df_patentes[df_patentes['Tipo Limpio'] == 'A']['Patente'].nunique()
            cant_b = df_patentes[df_patentes['Tipo Limpio'] == 'B']['Patente'].nunique()
            cant_c = df_patentes[df_patentes['Tipo Limpio'] == 'C']['Patente'].nunique()
            
            col_a, col_b, col_c = st.columns(3)
            if 'tipo_dano' not in st.session_state: st.session_state.tipo_dano = 'A'
            
            if col_a.button(f"DAÑO A ({cant_a} Vehículos)"): st.session_state.tipo_dano = 'A'
            if col_b.button(f"DAÑO B ({cant_b} Vehículos)"): st.session_state.tipo_dano = 'B'
            if col_c.button(f"DAÑO C ({cant_c} Vehículos)"): st.session_state.tipo_dano = 'C'
            
            tipo = st.session_state.tipo_dano
            df_final = df[(df['Tipo Limpio'] == tipo) & (df['Bloque'] != "OTRO / NO CLASIFICADO")]

            if not df_final.empty:
                resumen_bloques = df_final.groupby('Bloque')['Dif (2)'].mean().reset_index()
                resumen_bloques['Orden'] = resumen_bloques['Bloque'].str.extract(r'(\d+)').astype(int)
                resumen_bloques = resumen_bloques.sort_values('Orden')
                resumen_bloques['Tiempo (H:M)'] = resumen_bloques['Dif (2)'].apply(format_hours)

                st.subheader(f"Promedio de Tiempos - DAÑO {tipo}")
                
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

                st.subheader(f"Detalle de Actividades - DAÑO {tipo}")
                st.write("Tiempo promedio de cada tarea individual que compone los bloques superiores")
                
                resumen_detallado = df_final.groupby(['Bloque', 'Etapas'])['Dif (2)'].mean().reset_index()
                resumen_detallado['Orden'] = resumen_detallado['Bloque'].str.extract(r'(\d+)').astype(int)
                resumen_detallado = resumen_detallado.sort_values(['Orden', 'Dif (2)'], ascending=[True, False])
                resumen_detallado['Tiempo Promedio'] = resumen_detallado['Dif (2)'].apply(format_hours)
                
                tabla_mostrar = resumen_detallado[['Bloque', 'Etapas', 'Tiempo Promedio']].rename(columns={'Etapas': 'Actividad Específica'})
                st.dataframe(tabla_mostrar, use_container_width=True, hide_index=True)

            else:
                st.warning(f"No hay registros del Daño {tipo} clasificados en las fases estándar operativas.")

            # --- COMPARATIVA DE BLOQUES ---
            st.divider()
            st.subheader("📊 Comparativa de Tiempos por Bloque (Daño A vs B vs C)")
            st.write("Nota: Esta gráfica compara el tiempo promedio de cada bloque principal independientemente de las actividades internas que las componen")

            df_comp = df[(df['Tipo Limpio'].isin(['A', 'B', 'C'])) & (df['Bloque'] != "OTRO / NO CLASIFICADO")]

            if not df_comp.empty:
                resumen_comp = df_comp.groupby(['Bloque', 'Tipo Limpio'])['Dif (2)'].mean().reset_index()
                resumen_comp['Orden'] = resumen_comp['Bloque'].str.extract(r'(\d+)').astype(int)
                resumen_comp = resumen_comp.sort_values(['Orden', 'Tipo Limpio'])
                resumen_comp['Tiempo (H:M)'] = resumen_comp['Dif (2)'].apply(format_hours)

                fig_comp = px.bar(
                    resumen_comp,
                    x='Bloque',
                    y='Dif (2)',
                    color='Tipo Limpio',
                    barmode='group',
                    text='Tiempo (H:M)',
                    title=f"Comparativa General de Bloques - Mes: {mes_sel}",
                    labels={'Dif (2)': 'Promedio en Horas', 'Bloque': 'Fases del Taller', 'Tipo Limpio': 'Tipo de Daño'},
                    color_discrete_map={'A': '#00cc96', 'B': '#ff9900', 'C': '#ef553b'}
                )
                fig_comp.update_traces(textposition='outside', textfont_size=10)
                fig_comp.update_layout(yaxis_title="Horas Promedio", xaxis_title="", legend_title="Daño")
                st.plotly_chart(fig_comp, use_container_width=True)

            # --------------------------------------------------------------------------------
            # NUEVA SECCIÓN: LÍNEA DE VIDA POR VEHÍCULO (FLUJOGRAMA)
            # --------------------------------------------------------------------------------
            st.divider()
            st.subheader(f"🚗 Flujograma de Tiempos por Vehículo - DAÑO {tipo}")
            st.write("Visualiza el recorrido cronológico de cada vehículo (Patente). Cada segmento representa la suma de horas invertidas en ese bloque específico.")

            # Filtramos solo los que tienen patente real para este daño específico
            df_vehiculos = df_final[(df_final['Patente'] != 'NAN') & (df_final['Patente'] != '')].copy()

            if not df_vehiculos.empty:
                # Agrupar las horas invertidas por Patente y por Bloque
                df_gantt = df_vehiculos.groupby(['Patente', 'Bloque'])['Dif (2)'].sum().reset_index()
                
                # Le sacamos el número al bloque para ordenar cronológicamente la barra
                df_gantt['Orden'] = df_gantt['Bloque'].str.extract(r'(\d+)').astype(int)
                df_gantt = df_gantt.sort_values(['Patente', 'Orden'])
                df_gantt['Tiempo (H:M)'] = df_gantt['Dif (2)'].apply(format_hours)

                # Ordenar el eje Y (Patentes) para que los autos que tardaron MÁS queden arriba
                orden_patentes = df_gantt.groupby('Patente')['Dif (2)'].sum().sort_values(ascending=True).index
                # Lista de bloques ordenados del 1 al 10 para que se apilen correctamente
                orden_bloques = sorted(df_gantt['Bloque'].unique(), key=lambda x: int(x.split('.')[0]))

                # Gráfico de Barras Apiladas (Stacked Bar Chart)
                fig_vehiculos = px.bar(
                    df_gantt,
                    x='Dif (2)',
                    y='Patente',
                    color='Bloque',
                    orientation='h',
                    title=f"Tiempo Total de Intervención por Auto (Daño {tipo})",
                    labels={'Dif (2)': 'Total de Horas', 'Patente': 'Patente'},
                    hover_data={'Tiempo (H:M)': True, 'Dif (2)': False, 'Orden': False},
                    category_orders={'Patente': orden_patentes, 'Bloque': orden_bloques} # Fuerza el orden lógico
                )
                
                # Configuramos barmode='stack' para que se comporten como un flujo de tiempo
                fig_vehiculos.update_layout(
                    barmode='stack', 
                    height=max(400, len(orden_patentes) * 35), # Se estira automáticamente si hay muchos autos
                    legend_title="Flujo Técnico",
                    xaxis_title="Acumulado de Horas Trabajadas",
                    yaxis_title=""
                )
                
                st.plotly_chart(fig_vehiculos, use_container_width=True)
            else:
                st.warning(f"No hay registros de patentes válidas para graficar el flujograma del Daño {tipo}.")

        else:
            st.info(f"No hay datos cargados para {mes_sel}.")

    # --------------------------------------------------------------------------------
    # 5. SUBMENÚ: PRODUCTIVIDAD DE OPERARIOS
    # --------------------------------------------------------------------------------
    elif opcion == "👨‍🔧 Productividad de Operarios":
        st.title("👨‍🔧 Auditoría y Productividad de Operarios")
        
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            mes_op = st.selectbox("Mes:", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], key="mes_op")
        with col_filtro2:
            tipo_dano_op = st.selectbox("Tipo de Daño a auditar:", ["A", "B", "C"], key="dano_op")
        
        if mes_op == "Enero":
            df_op_filtrado = df[(df['Tipo Limpio'] == tipo_dano_op) & (df['Bloque'] != "OTRO / NO CLASIFICADO")]
            
            if not df_op_filtrado.empty:
                st.divider()
                st.subheader(f"Matriz de Eficiencia - DAÑO {tipo_dano_op}")
                
                bloque_sel = st.selectbox("Seleccione Fase Técnica para analizar al personal:", list(MAPEO_BLOQUES.keys()))
                df_bloque = df_op_filtrado[df_op_filtrado['Bloque'] == bloque_sel]
                
                if not df_bloque.empty:
                    avg_ref = df_bloque['Dif (2)'].mean()
                    
                    df_ranking = df_bloque.groupby('Operario').agg(
                        Tiempo_Promedio=('Dif (2)', 'mean'),
                        Vehiculos=('Ref.OR', 'nunique')
                    ).reset_index()
                    
                    panos_reales = df_bloque.groupby(['Operario', 'Ref.OR'])['PAÑOS'].first().groupby('Operario').sum().reset_index()
                    df_ranking = df_ranking.merge(panos_reales, on='Operario', how='left')
                    
                    df_ranking['Estado'] = df_ranking['Tiempo_Promedio'].apply(lambda x: '⚠️ Lento' if x > avg_ref else '✅ Rápido/Eficiente')
                    df_ranking['Tiempo (H:M)'] = df_ranking['Tiempo_Promedio'].apply(format_hours)
                    df_ranking = df_ranking.sort_values('Tiempo_Promedio', ascending=True)

                    fig_ranking = px.bar(
                        df_ranking, 
                        x='Tiempo_Promedio', 
                        y='Operario', 
                        color='Estado',
                        orientation='h',
                        text='Tiempo (H:M)',
                        hover_data={'Vehiculos': True, 'PAÑOS': True, 'Tiempo_Promedio': False},
                        title=f"Desempeño en {bloque_sel} (Línea punteada = Promedio {format_hours(avg_ref)})",
                        color_discrete_map={'✅ Rápido/Eficiente': '#00cc96', '⚠️ Lento': '#ef553b'}
                    )
                    fig_ranking.add_vline(x=avg_ref, line_dash="dash", line_color="black")
                    fig_ranking.update_traces(textposition='inside')
                    fig_ranking.update_layout(xaxis_title="Promedio en Horas", yaxis_title="")
                    
                    st.plotly_chart(fig_ranking, use_container_width=True)

                    st.divider()
                    st.subheader("🔎 Ficha Técnica de Operario (Deep Dive)")
                    operario_sel = st.selectbox("Seleccione un técnico para auditar su volumen:", df_ranking['Operario'].tolist())
                    
                    datos_op = df_ranking[df_ranking['Operario'] == operario_sel].iloc[0]
                    
                    col_met1, col_met2, col_met3 = st.columns(3)
                    col_met1.metric("Tiempo Promedio en la Fase", datos_op['Tiempo (H:M)'], delta="Por debajo del límite" if datos_op['Tiempo_Promedio'] <= avg_ref else "Excede límite", delta_color="inverse")
                    col_met2.metric("Vehículos Intervenidos", int(datos_op['Vehiculos']))
                    col_met3.metric("Volumen (Paños Trabajados)", int(datos_op['PAÑOS']) if pd.notnull(datos_op['PAÑOS']) else 0)
                    
                    st.divider()
                    st.subheader("🚗 Auditoría de Patentes Críticas (Responsabilidad)")
                    st.write(f"Casos donde **{operario_sel}** superó el tiempo promedio esperado de **{format_hours(avg_ref)}** en **{bloque_sel}**.")
                    
                    df_lentos_op = df_bloque[(df_bloque['Operario'] == operario_sel) & (df_bloque['Dif (2)'] > avg_ref)].sort_values(by='Dif (2)', ascending=False)
                    
                    if not df_lentos_op.empty:
                        df_lentos_op['Tiempo Real (H:M)'] = df_lentos_op['Dif (2)'].apply(format_hours)
                        df_lentos_op['Paños del Vehículo'] = df_lentos_op['PAÑOS'].fillna(0).astype(int)
                        
                        tabla_auditoria = df_lentos_op[['Patente', 'Ref.OR', 'Etapas', 'Paños del Vehículo', 'Tiempo Real (H:M)']].rename(columns={'Etapas': 'Actividad'})
                        st.dataframe(tabla_auditoria, use_container_width=True, hide_index=True)
                    else:
                        st.success(f"Excelente: {operario_sel} no tiene vehículos críticos en esta fase para el Daño {tipo_dano_op}.")
                        
                else:
                    st.warning(f"No hay registros técnicos para la fase '{bloque_sel}' en Daño {tipo_dano_op}.")
            else:
                st.warning(f"No hay registros del Daño {tipo_dano_op} en este mes.")
        else:
            st.info(f"No hay datos de operarios cargados para el mes de {mes_op}.")

except Exception as e:
    st.error(f"Error general en el sistema: {e}")
