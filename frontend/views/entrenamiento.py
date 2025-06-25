import sys
import os
import logging
import streamlit as st
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import load_config

st.set_page_config(page_title="Entrenamiento Vector Store")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/app_debug.log', encoding='utf-8')],
    encoding='utf-8',
)

logger = logging.getLogger(__name__)
CONFIG_JSON = load_config()
API_ENDPOINTS_BASE = CONFIG_JSON['api_endpoints_base']
API_TRAINING = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['training']

def main():
    st.title("🧠 Entrenamiento del Agente SQL")
    st.caption("Esta herramienta es solo para uso interno del equipo de desarrollo.")

    API_URL = API_TRAINING

    tipo = st.selectbox("Tipo de contenido a entrenar", ["sql", "ddl", "docs"])
    question = st.text_area("Pregunta (o descripción que da contexto)", height=100)
    content = st.text_area("Contenido a almacenar (SQL, DDL o Documento)", height=200)

    if st.button("Enviar ᯓ➤"):
        if not question or not content:
            st.warning("Por favor completa todos los campos.")
        else:
            payload = {
                "type": tipo,
                "question": question,
                "content": content
            }
            logger.info(f"Payload: {payload}")
            try:
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    st.toast("✅ Ejemplo entrenado correctamente.")
                else:
                    st.error(f"❌ Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Error al conectar con el backend: {e}")
        st.rerun()

main()