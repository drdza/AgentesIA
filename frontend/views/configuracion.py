
import streamlit as st
import os
import json
import datetime

st.set_page_config(page_title="Configuraciones", layout="wide")
st.title("⚙️ Configuración del Agente SQL")

# Ruta de logs y prompts
LOG_PATH = "logs/app_debug.log"
PROMPT_PATHS = {
    "Reformulación": "prompts/question_enhancer.txt",
    "Flujo Técnico": "prompts/flow_generator_prompt.txt",
    "SQL Generado": "prompts/system_context.txt"
}

# Cargar configuración previa (si decides persistirla en JSON)
CONFIG_FILE = "shared/config.json"
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    raise

st.markdown("##### 🛠️ Opciones del Agente")

col1, col2 = st.columns(2)
with col1:
    st.checkbox("Reformular pregunta", value=config["opciones"]["reformular"])
with col2:
    st.checkbox("Guardar Evento", value=config["opciones"]["evento"])

st.divider()

st.markdown("##### 🤖 Modelos por Tarea")

col1, col2, col3 = st.columns(3)

with col1:
    st.text_area("**🔁 Modelo para Reformulación**", config["modelos"]['modelo_enhancer'], disabled=True, height=70)
with col2:
    st.text_area("**🧭 Modelo para Flujo Técnico**", config["modelos"]['modelo_flujo'], disabled=True, height=70)
with col3:
    st.text_area("**💻 Modelo para Generación SQL**", config["modelos"]['modelo_sql'], disabled=True, height=70)


