import streamlit as st
import base64

# 1. Configuración de página
st.set_page_config(
    page_title="Taller CENOA Jujuy - Análisis de Tiempos",
    page_icon="📊",
    layout="wide"
)

# 2. Función para cargar imágenes locales y usarlas en CSS
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# NOTA: Asegúrate de que los archivos 'logo-taller-cenoa.png' y 
# 'WhatsApp Image 2026-03-09 at 09.16.01.jpeg' estén en la misma carpeta que app.py en GitHub.

try:
    background_bin = get_base64_of_bin_file('WhatsApp Image 2026-03-09 at 09.16.01.jpeg')
    
    # Inyectar CSS para el fondo y estilo
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(255,255,255,0.85), rgba(255,255,255,0.85)), url("data:image/jpge;base64,{background_bin}");
            background-size: cover;
            background-attachment: fixed;
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.9);
        }}
        h1 {{
            color: #002366;
            font-family: 'Arial Black';
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except:
    st.warning("No se pudo cargar la imagen de fondo. Verifica que el nombre del archivo en GitHub coincida exactamente.")

# 3. Sidebar (Columna Lateral)
with st.sidebar:
    # Mostrar Logo
    try:
        st.image("logo-taller-cenoa.png", use_container_width=True)
    except:
        st.write("### TALLER CENOA")
    
    st.divider()
    st.title("Navegación")
    
    # Submenús
    opcion = st.radio(
        "Seleccione un análisis:",
        ["🏠 Inicio", "📈 Eficiencia por Daño", "👨‍🔧 Productividad de Operarios"],
        index=0
    )
    
    st.divider()
    st.info("Sistema de Gestión de Calidad - Jujuy")

# 4. Contenido de las Páginas
if opcion == "🏠 Inicio":
    st.title("Análisis de tiempo - Taller CENOA Jujuy")
    st.subheader("Bienvenido al Portal de Auditoría")
    st.write("""
        Esta plataforma permite visualizar en tiempo real el flujo de trabajo del taller, 
        identificando cuellos de botella y niveles de eficiencia en las etapas de Chapa y Pintura.
        
        **Seleccione una opción en el menú de la izquierda para comenzar.**
    """)

elif opcion == "📈 Eficiencia por Daño":
    st.title("📈 Análisis de Eficiencia por Daño")
    st.write("Página en construcción... (Aquí irá el semáforo de KPIs que trabajamos)")

elif opcion == "👨‍🔧 Productividad de Operarios":
    st.title("👨‍🔧 Productividad de Operarios")
    st.write("Página en construcción... (Aquí irá el ranking y las patentes críticas)")
