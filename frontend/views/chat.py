
import sys
import os
import streamlit as st
import requests
import pandas as pd
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import load_config

CONFIG_JSON = load_config()
API_ENDPOINTS_BASE = CONFIG_JSON['api_endpoints_base']

st.set_page_config(page_title="Agente SQL", layout="wide")

logger = logging.getLogger("streamlit_agent_sql")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

st.title("🧠 Agente SQL - Consultas automáticas")

pregunta = st.text_input("📥 Escribe tu pregunta:", placeholder="¿Cuántos tickets se resolvieron fuera del SLA este mes?")
dominio = "tickets"  # Por ahora fijo, podrías hacerlo dinámico

if st.button("🔍 Consultar"):
    if not pregunta.strip():
        st.warning("Debes ingresar una pregunta.")
        st.stop()

    with st.spinner("Generando consulta..."):
        try:
            response = requests.post(f"{API_ENDPOINTS_BASE}/generate_sql", json={"question": pregunta, "domain": dominio})
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            st.error("❌ Ocurrió un error al procesar tu solicitud.")
            logger.error(f"❌ Error al consultar agente SQL: {e}", exc_info=True)
            st.stop()

    st.markdown("### 🧪 Flujo técnico propuesto:")
    st.code(data['flow'], language="markdown")

    st.markdown("### 📜 SQL generado:")
    st.code(data['sql'], language="sql")

    st.markdown("### 📊 Resultado de la consulta:")
    if data["result"]:        
        df = pd.DataFrame(data['result']["rows"], columns=data['result']["columns"])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No se obtuvo ningún resultado desde la base de datos.")

    st.markdown("### 🧠 ¿Es correcta esta respuesta del agente?")
    edited_sql = st.text_area("📝 Puedes editar el SQL si es necesario:", value=data['sql'], height=150)

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("👍 Aprobar y entrenar al agente", use_container_width=True):
            payload = {
                "type": "sql",
                "question": data['reformulation'],
                "content": edited_sql,
                "tag": dominio
            }
            try:
                response = requests.post(f"{API_ENDPOINTS_BASE}/train", json=payload)
                response.raise_for_status()
                st.success("✅ Entrenamiento exitoso. El agente ha aprendido esta respuesta.")
            except Exception as e:
                st.error("❌ Error al guardar la respuesta.")
                logger.error(f"❌ Fallo al entrenar con SQL aprobado\n{e}", exc_info=True)

    with cols[1]:
        st.button("👎 Rechazar respuesta", use_container_width=True)
