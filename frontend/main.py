# main.py
import logging
import streamlit as st

# Configurar logger
logging.basicConfig(level=logging.INFO)  # Nivel INFO o DEBUG
logger = logging.getLogger(__name__)



# Definir las páginas con títulos e iconos personalizados
pages = [    
    st.Page("views/chat.py", title="🤖 Agente SQL"),
    #st.Page("views/agente_sql.py", title="🤖 Agente SQL"),
    #st.Page("views/entrenamiento_vs.py", title="💾 Entrenamiento"),
    #st.Page("sites/configuracion.py", title="⚙️ Configuración del agente"),
    #st.Page("sites/editor_prompts.py", title="✏️ Editar Prompts"),
    #st.Page("views/eventos.py", title="🚀 Eventos"),
    #st.Page("sites/logs.py", title="🧾 Logs")
]

# Configurar la navegación
selected_page = st.navigation(pages)

# Ejecutar la página seleccionada
selected_page.run()
