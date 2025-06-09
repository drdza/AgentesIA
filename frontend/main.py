# main.py
import streamlit as st


# Definir las páginas con títulos e iconos personalizados
pages = [
    st.Page("views/agente_sql.py", title="🤖 Agente SQL"),
    st.Page("views/entrenamiento_vs.py", title="💾 Entrenamiento"),
    #st.Page("sites/configuracion.py", title="⚙️ Configuración del agente"),
    #st.Page("sites/editor_prompts.py", title="✏️ Editar Prompts"),
    #st.Page("sites/eventos.py", title="🚀 Eventos"),
    #st.Page("sites/logs.py", title="🧾 Logs")
]

# Configurar la navegación
selected_page = st.navigation(pages)

# Ejecutar la página seleccionada
selected_page.run()
