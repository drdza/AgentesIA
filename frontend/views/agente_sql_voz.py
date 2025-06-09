import sys
import os
import requests
import time
import logging
import streamlit as st
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import load_prompt_template, load_config

st.set_page_config(page_title="Agente SQL")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/app_debug.log', encoding='utf-8')],
    encoding='utf-8',
)

logger = logging.getLogger(__name__)

CONFIG_JSON = load_config()
API_ENDPOINTS_BASE = CONFIG_JSON['api_endpoints_base']
API_SQL = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['generate_sql']
API_AUDIO = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['transcribe_audio']

st.title("🤖 Agente SQL")
st.markdown("💭 Haz una pregunta y permite que la **Inteligencia Artificial** te responda.")

dominio = "tickets"
audio_bytes = st.audio_input("🗣 Usa tu voz para preguntarle a la IA.")

def load_init_prompts(domain: str):
    if 'prompts' not in st.session_state:
        st.session_state.prompts = {
            'enhancer': load_prompt_template(domain=domain, template_name="question_enhancer.txt"),
            'flow': load_prompt_template(domain=domain, template_name="flow_generator_prompt.txt"),
            'sql': load_prompt_template(domain=domain, template_name="system_context.txt")
        }

if audio_bytes:
    load_init_prompts(dominio)
    try:
        with st.status("🗣️ Transcribiendo pregunta...") as status:
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            response = requests.post(API_AUDIO, files=files)
            response.raise_for_status()
            transcribed = response.json()["text"]
            st.info(f"📥 Pregunta: {transcribed}")
            
            status.update(label= "🧠 Ejecutando agente de IA...")
            time.sleep(1)

            sql_response = requests.post(API_SQL, json={"question": transcribed, "domain": dominio})
            sql_response.raise_for_status()
            data = sql_response.json()
            contain_error = True if "error" in data['result'] else False

            status.update(label= "🧠 Preparando resultados...")
            time.sleep(1)

            if contain_error:
                tabs = st.tabs(["🧠 Reformulación", "📘 Flujo Técnico", "💻 SQL Generado", "❌ Error"])
            else:
                tabs = st.tabs(["🧠 Reformulación", "📘 Flujo Técnico", "💻 SQL Generado"])            
                        
            with tabs[0]:
                st.markdown(data['reformulation'])
            with tabs[1]:
                st.markdown(data['flow'])
            with tabs[2]:
                st.code(data['sql'], language="sql")

            status.update(label= "🧠 Mostrando resultados...")
            time.sleep(1)

            if contain_error:
                status.update(label="😵 Tarea completada con errores.")
            else:
                status.update(label="✅ Tarea completada con éxito")

        # Resultado fuera del status        
        if contain_error:
            with tabs[3]:
                st.error(f"❌ Error al ejecutar SQL: {data['result']['error']}")
            st.error("❌ Lamentamos lo ocurrido al procesar su pregunta. Se ha registrado el evento y se ha informado al administrador.")
            st.info("💡 Le sugerimos cambiar el enfoque de la pregunta y volverlo a intentar.")            
            logger.error(f"❌ Error al ejecutar el SQL\n{data['result']}", exc_info=True)             
        else:
            st.markdown("### 📊 Resultado")
            df = pd.DataFrame(data['result']["rows"], columns=data['result']["columns"])
            st.dataframe(df, use_container_width=True)            

    except Exception as e:
        st.error(f"❌ Error durante la ejecución: {e}")

st.divider()
st.caption(f" 🧠 **InnovAI** puede cometer errores. El modelo utiliza datos de **{dominio}** para responder tus preguntas.")
st.caption(" 👨🏻‍💻 Desarrollado por el equipo de IE – Grupo Reyma")