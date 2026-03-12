import streamlit as st
import pandas as pd
import io
import requests
import plotly.express as px
from datetime import timedelta

# 1. CONFIGURACIÓN DE PÁGINA MODO PRO
st.set_page_config(page_title="Taller CENOA Jujuy - Análisis Técnico", layout="wide", page_icon="📈")

# Estilo corporativo avanzado
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    div[data-testid="stMetricValue"] { font-size: 22px !important; } 
    div[data-testid="column"] > button { width: 100%; height: 50px; font-weight: bold; border-radius: 8px; border: 2px solid #002366; color: #002366; transition: all 0.3s; }
    div[data-testid="column"] > button:hover { background-color: #002366; color: #ffffff; transform: scale(1.02); }
    div[data-testid="column"] > button:active { transform: scale(0.98); }
    .sidebar-footer { position: fixed; bottom: 20px; width: 260px; font-size: 11px; color: #666; padding: 10px; border-top: 1px solid #ddd; }
    h1, h2, h3 { color: #002366; font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES MATEMÁTICAS Y DE TIEMPO
def format_hours(decimal_hours):
    if pd.isna(decimal_hours) or decimal_hours <= 0: return "0h 00m"
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60: hours += 1; minutes = 0
    return f"{hours}h {minutes:02d}m"

def extract_day(val):
    try:
        val_str = str(val).strip()
        if val_str.upper() in ['NAN', 'NAT', 'NULL', 'NONE', '']: return None
        dt = pd.to_datetime(val_str, errors='coerce', dayfirst=True)
        if pd.notna(dt): return dt.day
        if '/' in val_str: return int(val_str.split('/')[0])
        elif '-' in val_str:
            parts = val_str.split(' ')[0].split('-')
            return int(parts[2]) if len(parts[0]) == 4 else int(parts[0])
        val_float = float(val_str)
        if val_float > 40000:
            dt = pd.to_datetime('1899-12-30') + pd.to_timedelta(val_float, 'D')
            return dt.day
        else: return int(val_float)
    except: return None

def create_dt(day, time_str):
    if pd.isna(day) or not time_str or str(time_str).upper() in ['NAN', 'NAT', 'NONE', '']: return pd.NaT
    try:
        time_str = str(time_str).strip()
        if ' ' in time_str: time_str = time_str.split()[-1]
        parts = time_str.split(':')
        if len(parts) >= 2:
            return pd.Timestamp(year=2026, month=1, day=int(day), hour=int(parts[0]), minute=int(parts[1]))
    except: pass
    return pd.NaT

DIAS_VALIDOS = [2, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23, 26, 27, 28, 29, 30]

# --- MOTOR EXPERTO DE HORAS HÁBILES ---
def get_time_in_hours(t): return t.hour + t.minute / 60.0

def active_hours_in_day(t_start_hrs, t_end_hrs):
    p1_start = max(8.5, t_start_hrs)
    p1_end = min(13.0, t_end_hrs)
    p1_dur = max(0, p1_end - p1_start)
    
    p2_start = max(14.0, t_start_hrs)
    p2_end = min(18.5, t_end_hrs)
    p2_dur = max(0, p2_end - p2_start)
    return p1_dur + p2_dur

def calc_working_hours(start_dt, end_dt):
    if pd.isna(start_dt) or pd.isna(end_dt): return 0.0
    if start_dt >= end_dt: return 0.0

    d1, d2 = start_dt.day, end_dt.day
    h1, h2 = get_time_in_hours(start_dt), get_time_in_hours(end_dt)

    if d1 == d2:
        return active_hours_in_day(h1, h2) if d1 in DIAS_VALIDOS else 0.0

    total_hours = 0.0
    if d1 in DIAS_VALIDOS: total_hours += active_hours_in_day(h1, 24.0)
    for d in DIAS_VALIDOS:
        if d1 < d < d2: total_hours += 9.0
    if d2 in DIAS_VALIDOS: total_hours += active_hours_in_day(0.0, h2)
    return total_hours

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
            
        if 'Fecha' not in df.columns:
            cols_fecha = [c for c in df.columns if 'fech' in c.lower()]
            if cols_fecha: df.rename(columns={cols_fecha[0]: 'Fecha'}, inplace=True)
            else: df['Fecha'] = ''

        df['Day'] = df['Fecha'].apply(extract_day)
        df['Start_DT'] = df.apply(lambda r: create_dt(r['Day'], r['Entra (2)']), axis=1)
        df['End_DT'] = df.apply(lambda r: create_dt(r['Day'], r['Salid (2)']), axis=1)
        
        df['Dif (2)'] = pd.to_numeric(df['Dif (2)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        df['PAÑOS'] = pd.to_numeric(df['PAÑOS'], errors='coerce')
        df['Operario'] = df['Operario'].astype(str).str.upper().str.strip()
        df['Etapas'] = df['Etapas'].astype(str).str.upper().str.strip()
        df['Tipo de Daño'] = df['Tipo de Daño'].astype(str).str.upper().str.strip()
        df['Patente'] = df['Patente'].astype(str).str.upper().str.strip() 
        return df
    except Exception: return pd.DataFrame()

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
    for b, sub in MAPEO_BLOQUES.items():
        if etapa in sub: return b
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
        st.error("🚨 Error crítico: No se pudieron descargar los datos.")
        st.stop()
        
    excluir_ops = ["ANDREA MARTINS", "JAVIER GUTIERREZ", "SAMUEL ANTUNEZ"]
    df = df_raw[~df_raw['Operario'].isin(excluir_ops)].copy()
    df['Bloque'] = df['Etapas'].apply(obtener_bloque)
    df['Tipo Limpio'] = df['Tipo de Daño'].apply(limpiar_dano)

    day_start_x = {d: i * 9 for i, d in enumerate(DIAS_VALIDOS)}

    # 4. SIDEBAR
    with st.sidebar:
        st.title("Taller CENOA")
        opcion = st.radio("Navegación:", ["🏠 Inicio", "📈 Análisis tipo de DAÑOS", "📊 Flujo General Promedio"], label_visibility="collapsed")
        st.markdown("""<div class="sidebar-footer"><b>Taller de Chapa y Pintura CENOA Jujuy</b><br>Las Lomas 2227</div>""", unsafe_allow_html=True)

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
    # 6. SUBMENÚ: ANÁLISIS TIPO DE DAÑOS
    # --------------------------------------------------------------------------------
    elif opcion == "📈 Análisis tipo de DAÑOS":
        st.title("📈 Análisis tipo de DAÑOS")
        mes_sel = st.selectbox("Seleccione el mes:", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        
        if mes_sel == "Enero":
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
                df_vehiculos = df_final[(df_final['Patente'] != 'NAN') & (df_final['Patente'] != '') & (df_final['Day'].notna())].copy()

                if not df_vehiculos.empty:
                    plot_data = []
                    for patente, df_veh in df_vehiculos.groupby('Patente'):
                        dias_activos = [d for d in df_veh['Day'].unique() if d in DIAS_VALIDOS]
                        if not dias_activos: continue
                        min_day_idx, max_day_idx = min([DIAS_VALIDOS.index(d) for d in dias_activos]), max([DIAS_VALIDOS.index(d) for d in dias_activos])
                        
                        for idx in range(min_day_idx, max_day_idx + 1):
                            current_day = DIAS_VALIDOS[idx]
                            base_x = day_start_x[current_day]
                            df_day = df_veh[df_veh['Day'] == current_day]
                            is_last_day = (idx == max_day_idx)
                            
                            if df_day.empty:
                                plot_data.append({'Patente': patente, 'Bloque': '⏳ Mudas de trabajo', 'Duracion': 9.0, 'Base_Inicio': base_x, 'Texto': '9.00h (9h 00m)', 'Orden_Bloque': 99})
                            else:
                                day_grouped = df_day.groupby('Bloque')['Dif (2)'].sum().reset_index()
                                day_grouped['Orden_Bloque'] = day_grouped['Bloque'].str.extract(r'(\d+)').astype(int)
                                day_grouped = day_grouped.sort_values('Orden_Bloque')
                                
                                current_x = base_x
                                total_worked_today = 0
                                for _, row in day_grouped.iterrows():
                                    dur = row['Dif (2)']
                                    if dur > 0:
                                        plot_data.append({'Patente': patente, 'Bloque': row['Bloque'], 'Duracion': dur, 'Base_Inicio': current_x, 'Texto': f"{dur:.2f}h ({format_hours(dur)})", 'Orden_Bloque': row['Orden_Bloque']})
                                        current_x += dur; total_worked_today += dur
                                
                                muda = 9.0 - total_worked_today
                                if muda > 0.01 and not is_last_day: 
                                    plot_data.append({'Patente': patente, 'Bloque': '⏳ Mudas de trabajo', 'Duracion': muda, 'Base_Inicio': current_x, 'Texto': f"{muda:.2f}h ({format_hours(muda)})", 'Orden_Bloque': 99})

                    df_plot = pd.DataFrame(plot_data)
                    if not df_plot.empty:
                        total_real_global = df_plot[df_plot['Bloque'] != '⏳ Mudas de trabajo']['Duracion'].sum()
                        total_muda_global = df_plot[df_plot['Bloque'] == '⏳ Mudas de trabajo']['Duracion'].sum()

                        orden_patentes_df = df_plot.groupby('Patente')['Base_Inicio'].min().sort_values(ascending=False).index
                        color_map = {'⏳ Mudas de trabajo': '#e0e0e0'} 
                        orden_bloques = sorted([b for b in df_plot['Bloque'].unique() if b != '⏳ Mudas de trabajo'], key=lambda x: int(x.split('.')[0]))
                        colores_base = px.colors.qualitative.Plotly
                        for i, b in enumerate(orden_bloques): color_map[b] = colores_base[i % len(colores_base)]

                        tick_vals = [day_start_x[d] for d in DIAS_VALIDOS]
                        tick_texts = [f"{d:02d}/01" for d in DIAS_VALIDOS]

                        fig = px.bar(df_plot, x='Duracion', y='Patente', base='Base_Inicio', color='Bloque', orientation='h', text='Texto', hover_data={'Texto': True, 'Duracion': False, 'Base_Inicio': False, 'Orden_Bloque': False}, category_orders={'Patente': orden_patentes_df}, color_discrete_map=color_map)
                        fig.update_layout(width=1600, height=max(500, len(orden_patentes_df) * 60), showlegend=True, legend_title="Actividades", xaxis=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_texts, title="Días Laborables", gridcolor='rgba(200, 200, 200, 0.4)', range=[0, len(DIAS_VALIDOS) * 9]), yaxis=dict(title="", showgrid=True, gridcolor='rgba(150, 150, 150, 0.4)', gridwidth=1, griddash='dot'), hovermode="closest")
                        for val in tick_vals: fig.add_vline(x=val, line_dash="solid", line_color="black", opacity=0.3)
                        fig.update_traces(textposition='auto', textfont_size=10) 
                        
                        col_kpi, col_chart = st.columns([1.5, 8.5])
                        with col_kpi:
                            st.markdown("<div style='margin-top: 80px;'></div>", unsafe_allow_html=True)
                            st.markdown(f"### 📊 Total global")
                            st.write(f"Daño {tipo}")
                            st.metric(label="Horas Trabajadas", value=format_hours(total_real_global))
                            st.metric(label="Mudas Totales", value=format_hours(total_muda_global))
                        with col_chart: st.plotly_chart(fig, use_container_width=False, theme=None)
                        
                        st.divider()
                        st.subheader("🔎 Detalle del Diagrama para cada vehículo")
                        vehiculo_sel = st.selectbox("Seleccione un vehículo:", sorted(df_vehiculos['Patente'].unique()))
                        df_plot_ind = df_plot[df_plot['Patente'] == vehiculo_sel]
                        if not df_plot_ind.empty:
                            fig_ind = px.bar(df_plot_ind, x='Duracion', y='Patente', base='Base_Inicio', color='Bloque', orientation='h', text='Texto', hover_data={'Texto': True, 'Duracion': False, 'Base_Inicio': False, 'Orden_Bloque': False}, color_discrete_map=color_map)
                            fig_ind.update_layout(width=1600, height=200, showlegend=True, legend_title="Actividades", xaxis=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_texts, title="Días Laborables", gridcolor='rgba(200, 200, 200, 0.4)', range=[0, len(DIAS_VALIDOS) * 9]), yaxis=dict(title=""), hovermode="closest")
                            for val in tick_vals: fig_ind.add_vline(x=val, line_dash="solid", line_color="black", opacity=0.3)
                            fig_ind.update_traces(textposition='auto', textfont_size=11) 
                            st.plotly_chart(fig_ind, use_container_width=False, theme=None)

                            st.markdown(f"### Resumen de Patente")
                            col_res1, col_res2 = st.columns(2)
                            col_res1.metric("Tiempo Total Utilizado", format_hours(df_plot_ind[df_plot_ind['Bloque'] != '⏳ Mudas de trabajo']['Duracion'].sum()))
                            col_res2.metric("Mudas de Trabajo", format_hours(df_plot_ind[df_plot_ind['Bloque'] == '⏳ Mudas de trabajo']['Duracion'].sum()))
                            
                            st.markdown(f"### 📋 Detalle Operativo: {vehiculo_sel}")
                            df_veh_det = df_vehiculos[df_vehiculos['Patente'] == vehiculo_sel].copy()
                            df_veh_det['Orden'] = df_veh_det['Bloque'].str.extract(r'(\d+)').astype(int)
                            df_veh_det = df_veh_det.sort_values(['Orden', 'Dif (2)'], ascending=[True, False])
                            for b in df_veh_det['Bloque'].unique():
                                df_b = df_veh_det[df_veh_det['Bloque'] == b].copy()
                                st.markdown(f"**{b}**")
                                df_show = df_b[['Fecha', 'Operario', 'Etapas', 'Dif (2)']].copy()
                                df_show['Duración'] = df_show['Dif (2)'].apply(format_hours)
                                df_show.rename(columns={'Etapas': 'Actividad Específica'}, inplace=True)
                                st.dataframe(df_show[['Fecha', 'Operario', 'Actividad Específica', 'Duración']], hide_index=True, use_container_width=True)
                                st.caption(f"⏱️ Suma total en {b}: **{format_hours(df_b['Dif (2)'].sum())}**")
                                st.write("---") 

    # --------------------------------------------------------------------------------
    # 7. SUBMENÚ: FLUJO GENERAL PROMEDIO
    # --------------------------------------------------------------------------------
    elif opcion == "📊 Flujo General Promedio":
        st.title("📊 Análisis Global de Flujo y Tiempos Promedio")
        mes_sel = st.selectbox("Seleccione el mes a analizar:", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        
        if mes_sel == "Enero":
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
            df_gen = df[(df['Tipo Limpio'] == tipo) & (df['Bloque'] != "OTRO / NO CLASIFICADO")].copy()
            df_gen = df_gen[df_gen['Start_DT'].notna() & df_gen['End_DT'].notna()]

            if not df_gen.empty:
                st.divider()
                st.markdown("""
                **Análisis de Eficiencia Promedio por Fases:** El gráfico se lee de **Izquierda a Derecha**:
                1. **Muda 2 (Gris Oscuro - Izquierda):** Promedio de tiempo que el vehículo esperó inactivo *antes* de iniciar esta fase.
                2. **Trabajo Neto (Color - Centro):** Promedio general de horas reales de trabajo invertidas en esta etapa.
                3. **Muda 1 (Gris Claro - Derecha):** Promedio de tiempo de interrupciones, pausas o saltos de días que ocurrieron *durante* la ejecución de esta misma fase.
                """)

                lista_bloques = sorted(df_gen['Bloque'].unique(), key=lambda x: int(x.split('.')[0]))
                
                sum_work = {b: 0.0 for b in lista_bloques}
                count_work = {b: set() for b in lista_bloques}
                sum_muda1 = {b: 0.0 for b in lista_bloques}
                count_muda1 = {b: set() for b in lista_bloques}
                sum_muda2 = {b: 0.0 for b in lista_bloques}
                count_muda2 = {b: set() for b in lista_bloques}

                for patente, df_v in df_gen.groupby('Patente'):
                    df_v = df_v.sort_values('Start_DT')
                    
                    for _, r in df_v.iterrows():
                        sum_work[r['Bloque']] += r['Dif (2)']
                        count_work[r['Bloque']].add(patente)
                    
                    for i in range(len(df_v) - 1):
                        b_curr = df_v.iloc[i]['Bloque']
                        b_next = df_v.iloc[i+1]['Bloque']
                        if b_curr == b_next:
                            gap = calc_working_hours(df_v.iloc[i]['End_DT'], df_v.iloc[i+1]['Start_DT'])
                            if gap > 0:
                                sum_muda1[b_curr] += gap
                                count_muda1[b_curr].add(patente) 
                    
                    end_b = df_v.groupby('Bloque')['End_DT'].max()
                    start_b = df_v.groupby('Bloque')['Start_DT'].min()
                    
                    for k in range(len(lista_bloques) - 1):
                        b_prev = lista_bloques[k]
                        b_curr = lista_bloques[k+1] 
                        
                        if b_prev in end_b and b_curr in start_b:
                            if start_b[b_curr] >= end_b[b_prev]:
                                gap2 = calc_working_hours(end_b[b_prev], start_b[b_curr])
                                if gap2 > 0: 
                                    sum_muda2[b_curr] += gap2
                                    count_muda2[b_curr].add(patente)

                plot_data_avg = []
                for b in lista_bloques:
                    c_w = len(count_work[b])
                    c_m1 = len(count_muda1[b])
                    c_m2 = len(count_muda2[b])
                    
                    if c_m2 > 0:
                        avg_m2 = sum_muda2[b] / c_m2 
                        plot_data_avg.append({'Bloque': b, 'Componente': 'Muda 2 (Espera Inicio)', 'Promedio (Hs)': avg_m2, 'Texto': f"{format_hours(avg_m2)}"})
                    
                    if c_w > 0:
                        avg_w = sum_work[b] / c_w
                        plot_data_avg.append({'Bloque': b, 'Componente': f'{b}', 'Promedio (Hs)': avg_w, 'Texto': f"{format_hours(avg_w)}"})
                    
                    if c_m1 > 0:
                        avg_m1 = sum_muda1[b] / c_m1 
                        plot_data_avg.append({'Bloque': b, 'Componente': 'Muda 1 (Intra-Bloque)', 'Promedio (Hs)': avg_m1, 'Texto': f"{format_hours(avg_m1)}"})

                df_avg = pd.DataFrame(plot_data_avg)
                
                if not df_avg.empty:
                    colores_base = px.colors.qualitative.Plotly
                    color_map_avg = {
                        'Muda 1 (Intra-Bloque)': '#d3d3d3', 
                        'Muda 2 (Espera Inicio)': '#8b8b8b' 
                    }
                    for i, b in enumerate(lista_bloques):
                        color_map_avg[b] = colores_base[i % len(colores_base)]

                    orden_componentes = ['Muda 2 (Espera Inicio)'] + lista_bloques + ['Muda 1 (Intra-Bloque)']

                    fig_avg = px.bar(
                        df_avg,
                        x='Promedio (Hs)',
                        y='Bloque',
                        color='Componente',
                        orientation='h',
                        text='Texto',
                        title=f"Desglose de Tiempos Promedio - DAÑO {tipo}",
                        category_orders={
                            'Bloque': lista_bloques[::-1], 
                            'Componente': orden_componentes 
                        }, 
                        color_discrete_map=color_map_avg,
                        hover_data={'Texto': True, 'Promedio (Hs)': False, 'Bloque': False}
                    )
                    
                    fig_avg.update_layout(height=600, xaxis_title="Horas Promedio", yaxis_title="Fases de Trabajo", legend_title="Tiempos y Mudas", hovermode="closest")
                    fig_avg.update_traces(textposition='auto', textfont_size=12)
                    st.plotly_chart(fig_avg, use_container_width=True)
                    
                    # --- NUEVA HERRAMIENTA DE AUDITORÍA EXCLUSIVA PARA TI ---
                    with st.expander("🛠️ Panel de Auditoría de Promedios (Ver datos exactos)"):
                        st.markdown("Esta tabla te revela la 'caja negra' del gráfico: te muestra exactamente cuántas horas sumó el sistema, por cuántos vehículos dividió y cuáles son sus patentes.")
                        audit_data = []
                        for b in lista_bloques:
                            m1_autos = " - ".join(list(count_muda1[b])) if count_muda1[b] else "-"
                            m2_autos = " - ".join(list(count_muda2[b])) if count_muda2[b] else "-"
                            
                            audit_data.append({
                                'Fase': b,
                                'Total Hs Muda 1': format_hours(sum_muda1[b]),
                                'Cant. Autos Muda 1': len(count_muda1[b]),
                                'Patentes Afectadas (M1)': m1_autos,
                                'Total Hs Muda 2': format_hours(sum_muda2[b]),
                                'Cant. Autos Muda 2': len(count_muda2[b]),
                                'Patentes Afectadas (M2)': m2_autos
                            })
                            
                        st.dataframe(pd.DataFrame(audit_data), hide_index=True, use_container_width=True)

                else:
                    st.info("No hay datos suficientes para calcular promedios globales.")
            else:
                st.warning(f"No hay registros del Daño {tipo} clasificados en las fases estándar operativas.")

except Exception as e:
    st.error(f"Error general en el sistema: {e}")
