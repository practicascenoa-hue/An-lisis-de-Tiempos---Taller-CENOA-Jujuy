import streamlit as st
import base64

# 1. Configuración de página
st.set_page_config(
    page_title="Taller CENOA Jujuy - Análisis de Tiempos",
    page_icon="📊",
    layout="wide"
)

# 2. Función para procesar imágenes de fondo
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Inyectar Estilo y Fondo de Pantalla
try:
    bin_str = get_base64('fondo-taller.jpeg')
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url("data:image/jpeg;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        .main-title {{
            color: white;
            font-size: 60px;
            font-weight: bold;
            text-align: center;
            margin-top: 15%;
            text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
            font-family: 'Helvetica', sans-serif;
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.95);
        }}
        .sidebar-footer {{
            position: fixed;
            bottom: 20px;
            font-size: 12px;
            color: #555;
            padding: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except:
    st.error("Error al cargar 'fondo-taller.jpeg'. Verifica el nombre en tu repositorio.")

# 3. Sidebar (Menú Lateral)
with st.sidebar:
    st.write("### Taller CENOA")
    try:
        st.image("logo-taller-cenoa.png", use_container_width=True)
    except:
        st.warning("No se encontró 'logo-taller-cenoa.png'")
    
    st.divider()
    
    # Submenús
    opcion = st.radio(
        "Navegación:",
        ["🏠 Inicio", "📈 Eficiencia por Daño", "👨‍🔧 Productividad de Operarios"],
        label_visibility="collapsed"
    )
    
    # Footer de la Sidebar con la dirección solicitada
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

# 4. Contenido Principal
if opcion == "🏠 Inicio":
    # Solo el título con el diseño de fondo
    st.markdown('<p class="main-title">Análisis de tiempo - Taller CENOA Jujuy</p>', unsafe_allow_html=True)

elif opcion == "📈 Eficiencia por Daño":
    st.markdown('<h1 style="color:white; text-align:center;">📈 Eficiencia por Daño</h1>', unsafe_allow_html=True)
    # Aquí irá tu lógica de gráficos más adelante

elif opcion == "👨‍🔧 Productividad de Operarios":
    st.markdown('<h1 style="color:white; text-align:center;">👨‍🔧 Productividad de Operarios</h1>', unsafe_allow_html=True)
    # Aquí irá tu lógica de operarios más adelante
