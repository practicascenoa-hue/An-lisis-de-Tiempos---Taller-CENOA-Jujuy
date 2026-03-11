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
                # DIAGRAMA DE TIEMPOS POR VEHÍCULO (AQUÍ EMPEZAREMOS A TRABAJAR EL NUEVO GRÁFICO)
                # --------------------------------------------------------------------------------
                st.divider()
                st.subheader(f"🚗 Diagrama de Tiempos por Vehículo - DAÑO {tipo}")
                
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
                
                La barra a color indica el **tiempo real trabajado**. La barra gris (Mudas de trabajo) completa el espacio hasta igualar el tiempo del vehículo que más demoró en ese bloque, alineando así el inicio de la siguiente etapa para todos los vehículos.
                """)

                # AQUÍ IRÁ EL NUEVO CÓDIGO DEL GRÁFICO...

            else:
                st.warning(f"No hay registros del Daño {tipo} clasificados en las fases estándar operativas.")

        else:
            st.info(f"No hay datos cargados para {mes_sel}.")

except Exception as e:
    st.error(f"Error general en el sistema: {e}")
