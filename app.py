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
            
        # NUEVO MOTOR DE CÁLCULO DE HORAS (Ignora fechas y fines de semana del Excel)
        def parse_time(val):
            val = str(val).strip().upper()
            if val in ['', 'NAN', 'NAT', 'NULL', 'NONE']: return None
            if ' ' in val: 
                val = val.split(' ')[-1]
            try:
                parts = val.split(':')
                if len(parts) >= 2:
                    return float(parts[0]) + float(parts[1])/60.0
                return float(val)
            except:
                return None

        def calc_diff(row):
            en = parse_time(row.get('Entra (2)'))
            sa = parse_time(row.get('Salid (2)'))
            if en is not None and sa is not None:
                d = sa - en
                return d + 24.0 if d < 0 else d
            try:
                val = str(row.get('Dif (2)', 0)).replace(',', '.')
                return float(val) if pd.notna(float(val)) else 0.0
            except:
                return 0.0

        df['Dif (2)'] = df.apply(calc_diff, axis=1)
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
                # --------------------------------------------------------------------------------
                # LÍNEA DE VIDA Y TIEMPO MUERTO (ALINEADO AL MÁXIMO)
                # --------------------------------------------------------------------------------
                st.divider()
                st.subheader(f"🚗 Flujograma de Tiempos por Vehículo - DAÑO {tipo}")
                st.write("La barra a color indica el **tiempo real trabajado**. La barra gris (Tiempo Muerto) completa el espacio hasta igualar el tiempo del vehículo que más demoró en ese bloque, alineando así el inicio de la siguiente etapa para todos los vehículos.")

                df_vehiculos = df_final[(df_final['Patente'] != 'NAN') & (df_final['Patente'] != '')].copy()

                if not df_vehiculos.empty:
                    agrupado = df_vehiculos.groupby(['Patente', 'Bloque'])['Dif (2)'].sum().reset_index()
                    agrupado.rename(columns={'Dif (2)': 'Trabajo_Real'}, inplace=True)

                    max_por_bloque = agrupado.groupby('Bloque')['Trabajo_Real'].max().reset_index()
                    max_por_bloque.rename(columns={'Trabajo_Real': 'Max_Bloque'}, inplace=True)

                    agrupado = agrupado.merge(max_por_bloque, on='Bloque')
                    agrupado['Tiempo_Muerto'] = agrupado['Max_Bloque'] - agrupado['Trabajo_Real']
                    agrupado['Tiempo_Muerto'] = agrupado['Tiempo_Muerto'].apply(lambda x: x if x > 0.01 else 0)

                    orden_bloques = sorted(agrupado['Bloque'].unique(), key=lambda x: int(x.split('.')[0]))

                    base_dict = {}
                    current_base = 0
                    tick_vals = []
                    tick_texts = []

                    for b in orden_bloques:
                        base_dict[b] = current_base
                        tick_vals.append(current_base)
                        tick_texts.append(b.split('. ')[-1])
                        max_dur = max_por_bloque[max_por_bloque['Bloque'] == b]['Max_Bloque'].values[0]
                        current_base += (max_dur + 0.5) 

                    plot_data = []
                    for idx, row in agrupado.iterrows():
                        plot_data.append({
                            'Patente': row['Patente'],
                            'Bloque': row['Bloque'],
                            'Tipo': row['Bloque'],
                            'Duracion': row['Trabajo_Real'],
                            'Base_Inicio': base_dict[row['Bloque']],
                            'Orden': int(row['Bloque'].split('.')[0]),
                            'Texto': format_hours(row['Trabajo_Real'])
                        })
                        if row['Tiempo_Muerto'] > 0:
                            plot_data.append({
                                'Patente': row['Patente'],
                                'Bloque': row['Bloque'],
                                'Tipo': '⏳ Tiempo Muerto',
                                'Duracion': row['Tiempo_Muerto'],
                                'Base_Inicio': base_dict[row['Bloque']] + row['Trabajo_Real'],
                                'Orden': int(row['Bloque'].split('.')[0]) + 0.5,
                                'Texto': format_hours(row['Tiempo_Muerto']) + " (M)"
                            })

                    df_plot = pd.DataFrame(plot_data)
                    df_plot = df_plot.sort_values(['Patente', 'Orden'])

                    orden_patentes = agrupado.groupby('Patente')['Trabajo_Real'].sum().sort_values(ascending=True).index

                    color_map = {'⏳ Tiempo Muerto': '#e0e0e0'} 
                    colores_base = px.colors.qualitative.Plotly
                    for i, b in enumerate(orden_bloques):
                        color_map[b] = colores_base[i % len(colores_base)]

                    fig_vehiculos = px.bar(
                        df_plot,
                        x='Duracion',
                        y='Patente',
                        base='Base_Inicio',
                        color='Tipo',
                        orientation='h',
                        text='Texto', 
                        title=f"Línea de Vida Alineada y Tiempo Muerto (Daño {tipo})",
                        labels={'Duracion': 'Horas', 'Patente': 'Patente'},
                        hover_data={'Texto': True, 'Duracion': False, 'Base_Inicio': False, 'Orden': False, 'Tipo': False},
                        category_orders={'Patente': orden_patentes},
                        color_discrete_map=color_map
                    )

                    fig_vehiculos.update_layout(
                        height=max(400, len(orden_patentes) * 35),
                        showlegend=True,
                        legend_title="Actividad / Demora",
                        xaxis=dict(
                            tickmode='array',
                            tickvals=tick_vals,
                            ticktext=tick_texts, 
                            title="",
                            gridcolor='rgba(200, 200, 200, 0.2)'
                        ),
                        yaxis=dict(
                            title="",
                            showgrid=True, # LÍNEAS HORIZONTALES POR VEHÍCULO
                            gridcolor='rgba(150, 150, 150, 0.4)',
                            gridwidth=1,
                            griddash='dot'
                        )
                    )

                    for val in tick_vals:
                        fig_vehiculos.add_vline(x=val, line_dash="dot", line_color="gray", opacity=0.7)

                    fig_vehiculos.update_traces(textposition='auto', textfont_size=11)
                    st.plotly_chart(fig_vehiculos, use_container_width=True)
                else:
                    st.warning(f"No hay registros de patentes válidas para graficar el flujograma del Daño {tipo}.")

            else:
                st.warning(f"No hay registros del Daño {tipo} clasificados en las fases estándar operativas.")

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
