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

# Función robusta para extraer el DÍA del mes de la columna "Entra (2)"
def extract_day(val):
    try:
        val_str = str(val).strip().upper()
        if val_str in ['NAN', 'NAT', 'NULL', 'NONE', '']: return None
        # Si el formato es "02/01/2026 10:40"
        if '/' in val_str:
            return int(val_str.split('/')[0])
        # Si el formato es "2026-01-02 10:40:00"
        if '-' in val_str:
            parts = val_str.split(' ')[0].split('-')
            if len(parts[0]) == 4: return int(parts[2])
            return int(parts[0])
        return None
    except:
        return None

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
            
        # Extraer el Día
        df['Day'] = df['Entra (2)'].apply(extract_day)

        # Usar directamente la columna 'Dif (2)' original del Excel 
        # (ya que ahora filtramos y encapsulamos por días de 9hs, la suma dará exacto)
        df['Dif (2)'] = pd.to_numeric(df['Dif (2)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce')
        df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
        df['Etapas'] = df['Etapas'].astype(str).str.upper().str.strip()
        df['Tipo de Daño'] = df['Tipo de Daño'].astype(str).str.upper().str.strip()
        df['Patente'] = df['Patente'].astype(str).str.upper().str.strip() 
        
        return df
    except Exception:
        return pd.DataFrame()

# Mapeo actualizado de Bloques
MAPEO_BLOQUES = {
    "1. DESARME": ["DESARME", "DESARMADO", "DESARME Y CHAPA", "AYUDA DE DESARME DE CHAPA"],
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

    # Días laborables de Enero 2026 (Excluyendo fines de semana)
    DIAS_VALIDOS = [2, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 26, 27, 28, 29, 30]
    
    # Cada día equivale a un bloque de 9 horas en el eje X
    day_start_x = {d: i * 9 for i, d in enumerate(DIAS_VALIDOS)}

    # 4. SIDEBAR
    with st.sidebar:
        st.title("Taller CENOA")
        opcion = st.radio("Navegación:", ["🏠 Inicio", "📈 Análisis tipo de DAÑOS"], label_visibility="collapsed")
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
    # 5. SUBMENÚ: ANÁLISIS TIPO DE DAÑOS (CÓDIGO 2)
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
                st.divider()
                st.subheader(f"🚗 Diagrama de Tiempos y Mudas de trabajo (DAÑO {tipo})")
                
                st.markdown("""
                Para el analisis del diagrama se consideró un agrupamiento de actividades en Bloques:
                - **DESARME:** DESARME - DESARMADO - DESARME Y CHAPA - AYUDA DE DESARME DE CHAPA
                - **CHAPA:** CHAPA - MASILLADO Y LIJADO
                - **PREPARADO:** PREPARADO - PREPARADO PARAGOLPE - PREPARADO PARAGOLPE DELANTERO - PREPARADO CAPERUZA - PREPARADO DE TAPA DE BAUL - PREPARACION DE PARAGOLPE - EMPAPELADO - LIJADO - LIJADO PRIMER
                - **APLICACIÓN DE PRIMER:** APLICACION DE PRIMER
                - **COLORIMETRÍA:** COLORIMETRIA
                - **PINTADO:** PINTADO - PREPRACION Y PINTADO TEXTURADO PARAGOLPE
                - **ARMADO:** ARMADO - REEMPLAZO - REEMPLAZO DE VIDRIOS - REEMPLAZO PARABRISAS Y PULIDO - COLOCACION DE VIDRIO Y PULIDO
                - **PULIDO:** PULIDO - PULIDO Y LUSTRADO - LUSTRADO - LIJADO Y PULIDO - LIJADO Y LUSTRADO - ENCERADO Y PULIDO - PULIDO PARAGOLPE - PULIDO GUARDABARRO - PULIDO Y LASTRE
                - **LAVADO:** LAVADO - PULIDO Y LAVADO - LUSTRADO Y LAVADO - LIJADO, PULIDO Y LAVADO - LIJADO, PULIDO Y LUSTRADO DE PIEZAS PINTADA JUNTO CON LAVADO
                - **ENTREGA:** TERMINACIONES - LIMPIEZA
                
                **Nota de lectura:** El eje horizontal representa los días laborables del mes. Cada día contiene una capacidad de **9 horas netas**. Las barras de colores muestran el tiempo real agrupado por bloque en ese día. El espacio sobrante para completar las 9 horas se grafica en gris como **Mudas de trabajo**.
                """)

                # Filtrar vehículos con patente válida y fecha parseable
                df_vehiculos = df_final[(df_final['Patente'] != 'NAN') & (df_final['Patente'] != '') & (df_final['Day'].notna())].copy()

                if not df_vehiculos.empty:
                    plot_data = []
                    
                    # Agrupar por Patente para procesar auto por auto
                    for patente, df_veh in df_vehiculos.groupby('Patente'):
                        # Extraer los días en los que este auto tuvo actividad
                        dias_activos = df_veh['Day'].unique()
                        
                        # Filtramos solo los días que caen en nuestro calendario oficial
                        dias_activos = [d for d in dias_activos if d in DIAS_VALIDOS]
                        if not dias_activos: continue
                        
                        # Determinar el rango de estadía del vehículo en el taller
                        min_day_idx = min([DIAS_VALIDOS.index(d) for d in dias_activos])
                        max_day_idx = max([DIAS_VALIDOS.index(d) for d in dias_activos])
                        
                        # Iteramos día por día desde que entró hasta que salió
                        for idx in range(min_day_idx, max_day_idx + 1):
                            current_day = DIAS_VALIDOS[idx]
                            base_x = day_start_x[current_day]
                            
                            df_day = df_veh[df_veh['Day'] == current_day]
                            
                            if df_day.empty:
                                # Día completo sin tocar el auto = 9 Horas de Muda
                                plot_data.append({
                                    'Patente': patente,
                                    'Bloque': '⏳ Mudas de trabajo',
                                    'Duracion': 9.0,
                                    'Base_Inicio': base_x,
                                    'Texto': '9.00h (9h 00m)',
                                    'Orden_Bloque': 99
                                })
                            else:
                                # Agrupamos las actividades de ese mismo día por Bloque
                                day_grouped = df_day.groupby('Bloque')['Dif (2)'].sum().reset_index()
                                day_grouped['Orden_Bloque'] = day_grouped['Bloque'].str.extract(r'(\d+)').astype(int)
                                day_grouped = day_grouped.sort_values('Orden_Bloque')
                                
                                current_x = base_x
                                total_worked_today = 0
                                
                                # Graficamos las barras a color
                                for _, row in day_grouped.iterrows():
                                    dur = row['Dif (2)']
                                    if dur > 0:
                                        plot_data.append({
                                            'Patente': patente,
                                            'Bloque': row['Bloque'],
                                            'Duracion': dur,
                                            'Base_Inicio': current_x,
                                            'Texto': f"{dur:.2f}h ({format_hours(dur)})",
                                            'Orden_Bloque': row['Orden_Bloque']
                                        })
                                        current_x += dur
                                        total_worked_today += dur
                                
                                # Las horas que faltan para llegar a 9 se marcan como Muda
                                muda = 9.0 - total_worked_today
                                if muda > 0.05: # Ignoramos remanentes menores a 3 minutos
                                    plot_data.append({
                                        'Patente': patente,
                                        'Bloque': '⏳ Mudas de trabajo',
                                        'Duracion': muda,
                                        'Base_Inicio': current_x,
                                        'Texto': f"{muda:.2f}h ({format_hours(muda)})",
                                        'Orden_Bloque': 99
                                    })

                    # Construir DataFrame final
                    df_plot = pd.DataFrame(plot_data)
                    
                    if not df_plot.empty:
                        # Ordenar el eje Y (Patentes) según qué auto entró primero
                        # Primero ordenamos por el inicio más temprano, luego por patente
                        orden_patentes_df = df_plot.groupby('Patente')['Base_Inicio'].min().sort_values(ascending=False).index
                        
                        # Paleta de Colores
                        color_map = {'⏳ Mudas de trabajo': '#e0e0e0'} 
                        orden_bloques = sorted([b for b in df_plot['Bloque'].unique() if b != '⏳ Mudas de trabajo'], key=lambda x: int(x.split('.')[0]))
                        colores_base = px.colors.qualitative.Plotly
                        for i, b in enumerate(orden_bloques):
                            color_map[b] = colores_base[i % len(colores_base)]

                        # Configuración de los "Ticks" o Marcas del Eje X
                        tick_vals = [day_start_x[d] for d in DIAS_VALIDOS]
                        tick_texts = [f"{d:02d}/01" for d in DIAS_VALIDOS]

                        # Creación del Gráfico
                        fig = px.bar(
                            df_plot,
                            x='Duracion',
                            y='Patente',
                            base='Base_Inicio',
                            color='Bloque',
                            orientation='h',
                            text='Texto',
                            title=f"Calendario de Producción - Daño {tipo} (Enero 2026)",
                            labels={'Duracion': 'Horas Trabajadas', 'Patente': 'Patente'},
                            hover_data={'Texto': True, 'Duracion': False, 'Base_Inicio': False, 'Orden_Bloque': False},
                            category_orders={'Patente': orden_patentes_df},
                            color_discrete_map=color_map
                        )

                        fig.update_layout(
                            height=max(400, len(orden_patentes_df) * 45),
                            showlegend=True,
                            legend_title="Actividades",
                            xaxis=dict(
                                tickmode='array',
                                tickvals=tick_vals,
                                ticktext=tick_texts,
                                title="Días Laborables (Cada tramo equivale a 9 horas netas)",
                                gridcolor='rgba(200, 200, 200, 0.4)',
                                range=[0, len(DIAS_VALIDOS) * 9] # Fija el ancho total del mes
                            ),
                            yaxis=dict(
                                title="",
                                showgrid=True,
                                gridcolor='rgba(150, 150, 150, 0.4)',
                                gridwidth=1,
                                griddash='dot'
                            )
                        )

                        # Líneas verticales que separan cada día (cada 9 horas)
                        for val in tick_vals:
                            fig.add_vline(x=val, line_dash="solid", line_color="black", opacity=0.3)

                        fig.update_traces(textposition='auto', textfont_size=10)
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No se pudo construir el calendario. Verifique los formatos de fecha en la columna 'Entra (2)'.")
                else:
                    st.warning(f"No hay registros de patentes con fechas válidas para graficar el diagrama del Daño {tipo}.")

            else:
                st.warning(f"No hay registros del Daño {tipo} clasificados en las fases estándar operativas.")

        else:
            st.info(f"No hay datos cargados para {mes_sel}.")

except Exception as e:
    st.error(f"Error general en el sistema: {e}")
