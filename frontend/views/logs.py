# pages/logs.py

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

# Modelos disponibles (puedes extender esta lista según tus NIMs/NLPs disponibles)
modelos_disponibles = ["gemma", "mistral", "llama", "gpt-3.5", "gpt-4", "openhermes"]

# Cargar configuración previa (si decides persistirla en JSON)
CONFIG_FILE = "config.json"
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    config = {
        "modelo_enhancer": "gemma",
        "modelo_flujo": "mistral",
        "modelo_sql": "mistral"
    }

st.markdown("### 🤖 Selección de Modelos por Tarea")

config["modelo_enhancer"] = st.selectbox("🔁 Modelo para Reformulación de Preguntas", modelos_disponibles, index=modelos_disponibles.index(config["modelo_enhancer"]))
config["modelo_flujo"] = st.selectbox("🧭 Modelo para Flujo Técnico", modelos_disponibles, index=modelos_disponibles.index(config["modelo_flujo"]))
config["modelo_sql"] = st.selectbox("💻 Modelo para Generación SQL", modelos_disponibles, index=modelos_disponibles.index(config["modelo_sql"]))

if st.button("💾 Guardar Configuración"):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    st.success("✅ Configuración guardada correctamente")

# Visualización de rutas
st.markdown("### 📂 Rutas del Sistema")
st.code(f"📁 Log: {LOG_PATH}")
for nombre, ruta in PROMPT_PATHS.items():
    st.code(f"{nombre}: {ruta}")

# Ver últimos errores si el log existe
st.markdown("### 🧾 Últimos Errores (Log)")
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        ultimas = lines[-10:] if len(lines) > 10 else lines
        st.text_area("Log de Errores:", value="".join(ultimas), height=300)
else:
    st.info("No se encontró archivo de log.")
