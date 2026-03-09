import streamlit as st
import base64
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Taller CENOA Jujuy - Análisis de Tiempos",
    page_icon="📊",
    layout="wide"
)

# 2. FUNCIONES PARA MANEJO DE IMÁGENES
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def buscar_archivo(lista_nombres):
    for nombre in lista_nombres:
        if os.path.exists(nombre):
            return nombre
    return None

# Intentar cargar fondo (probando variantes detectadas en tus capturas)
archivo_fondo = buscar_archivo(['fondo-taller.jpeg', 'fondo-taller.jpeg.jpeg', 'WhatsApp Image 2026-03-09 at 09.16.01.jpeg'])
archivo_logo = buscar_archivo(['logo-taller-cenoa.png', 'logo-taller-cenoa.png.png'])

# Inyectar CSS personalizado
if archivo_fondo:
    bin_str = get_base64(archivo_fondo)
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)), url("data:image/jpeg;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        .main-title {{
            color: white;
            font-size: 65px;
            font-weight: bold;
            text-align: center;
            margin-top: 15%;
            text-shadow: 3px 3px 15px rgba(0,0,0,0.9);
            font-family: 'Helvetica Neue', sans-serif;
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.98);
        }}
        .sidebar-footer {{
            position: fixed;
            bottom: 20px;
            width: 260px;
            font-size: 11px;
            color: #444;
            line-height: 1.4;
            padding: 10px;
            border-top: 1px solid #eee;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# 3. SIDEBAR (MENÚ LATERAL)
with st.sidebar:
    st.write("### Taller CENOA")
    if archivo_logo:
        st.image(archivo_logo, use_container_width=True)
    
    st.divider()
    
    opcion = st.radio(
        "Navegación:",
        ["🏠 Inicio", "📈 Eficiencia por Daño", "👨‍🔧 Productividad de Operarios"],
        label_visibility="collapsed"
    )
    
    # Dirección solicitada
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

# 4. CONTENIDO PRINCIPAL
if opcion == "🏠 Inicio":
    # Título limpio solicitado
    st.markdown('<p class="main-title">Análisis de tiempo - Taller CENOA Jujuy</p>', unsafe_allow_html=True)

else:
    # Contenido para otras páginas (transparente para que se vea el fondo)
    st.markdown(f'<h1 style="color:white; text-align:center;">{opcion}</h1>', unsafe_allow_html=True)
    st.info("Cargando datos del servidor...")
