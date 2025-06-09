# pages/agente_sql.py

import sys
import os
import streamlit as st
import pandas as pd
import requests
import logging
import json
import sseclient
from traceback import format_exc

# Agrega ruta del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import load_prompt_template, load_config

# Configuración general
st.set_page_config(page_title="Agente SQL Inteligente", layout="wide")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/app_debug.log', encoding='utf-8')],
    encoding='utf-8',
)
logger = logging.getLogger(__name__)
config = load_config()

API_STREAM_URL = "http://localhost:8000/generate_sql_stream"

# Carga de prompts
def load_init_prompts(domain: str):
    if 'prompts' not in st.session_state:
        st.session_state.prompts = {
            'enhancer': load_prompt_template(domain=domain, template_name="question_enhancer.txt"),
            'flow': load_prompt_template(domain=domain, template_name="flow_generator_prompt.txt"),
            'sql': load_prompt_template(domain=domain, template_name="system_context.txt")
        }

# UI principal
st.title("🤖 Agente SQL Inteligente")
st.markdown("Formula una pregunta en lenguaje natural y deja que el agente de IA genere y ejecute la consulta SQL por ti.")

with st.form(key="sql_form"):
    pregunta_usuario = st.text_area(
        label="✍️ Escribe tu pregunta:",
        placeholder="Ej. ¿Cuántos tickets cerrados hubo este mes?",
        height=70,
    )
    enviar = st.form_submit_button("🚀 Ejecutar")
    dominio = "tickets"

if enviar and pregunta_usuario:
    load_init_prompts(dominio)

    # Estado inicial
    reformulada = ""
    flujo = ""
    sql_generado = ""
    resultado = None

    with st.status("🧠 Ejecutando agente de IA...", expanded=True) as status:
        try:
            response = requests.post(
                API_STREAM_URL,
                json={"question": pregunta_usuario, "domain": dominio},
                stream=True,
                timeout=300
            )
            client = sseclient.SSEClient(response)

            for event in client.events():
                if event.data.strip() == "[DONE]":
                    break

                data = json.loads(event.data)
                stage = data.get("stage")

                if stage == "reformulation":
                    reformulada = data["content"]
                    status.update(label="🧠 Reformulación completada", state="running")
                    st.markdown("#### 🧠 Reformulación")
                    st.markdown(reformulada)

                elif stage == "flow":
                    flujo = data["content"]
                    status.update(label="📘 Flujo técnico generado", state="running")
                    st.markdown("#### 📘 Flujo Técnico")
                    st.code(flujo, language="markdown")

                elif stage == "sql":
                    sql_generado = data["content"]
                    status.update(label="💻 SQL generado", state="running")
                    st.markdown("#### 💻 Consulta SQL Generada")
                    st.code(sql_generado, language="sql")

                elif stage == "result":
                    resultado = data["content"]
                    status.update(label="📊 Consulta ejecutada correctamente", state="complete")

                    st.markdown("#### 📊 Resultado")
                    if "error" in resultado:
                        st.error(f"Error al ejecutar SQL: {resultado['error']}")
                    else:
                        df = pd.DataFrame(resultado["rows"], columns=resultado["columns"])
                        st.dataframe(df, use_container_width=True)

                elif stage == "error":
                    st.error(f"❌ Error: {data['message']}")
                    status.update(label="❌ Fallo durante el procesamiento", state="error")

                elif stage == "message":
                    st.info(data["message"])

                elif stage == "done":
                    st.success("✅ Agente completó el proceso.")
                    break

        except Exception as e:
            st.error("⚠️ Error al conectar con el backend.")
            logger.error("Error en procesamiento", exc_info=True)

st.divider()
st.caption("🧠 Este agente utiliza modelos de lenguaje para interpretar y generar SQL. Puede cometer errores.")
st.caption("👨🏻‍💻 Desarrollado por el equipo de IE – Grupo Reyma")
