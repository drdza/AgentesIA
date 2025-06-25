# pages/agente_sql.py

import sys
import os
import requests
import logging
import time
import streamlit as st
import pandas as pd
from traceback import format_exc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import load_config

CONFIG_JSON = load_config()
API_ENDPOINTS_BASE = CONFIG_JSON['api_endpoints_base']
API_SQL_GENERATION = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['generate_sql']
API_SQL_TRAINING = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['training']
API_SQL_EXECUTION = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['execute_sql']

logging.basicConfig(level=logging.INFO)  # Nivel INFO o DEBUG
logger = logging.getLogger(__name__)
st.set_page_config(page_title="Agente SQL")


def _load_local_css(file_path: str):
    with open(file_path, "r") as f:
        css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

css_path ="frontend/css/style.css"
_load_local_css(css_path)


with st.form(key="sql_form"):
    st.title("🤖 Agente SQL")
    st.markdown("💭 Haz una pregunta y permite que la **Inteligencia Artificial** te responda.")
    pregunta_usuario = st.text_area(
        label="✍️ Escribe tu pregunta:",
        placeholder="Ej. ¿Cuántos tickets cerrados hubo este mes?",
        height=70,
        value=st.session_state.get("transcribed_text", "")
    )
    enviar = st.form_submit_button("ᯓ➤")                  
    dominio = "tickets"
    
if enviar and pregunta_usuario:
    st.session_state["last_question"] = pregunta_usuario

    try:
        sql_response = requests.post(API_SQL_GENERATION,json={"question": pregunta_usuario, "domain": dominio})
        sql_response.raise_for_status()
        data = sql_response.json()
        st.session_state["last_response"] = data
    except requests.exceptions.HTTPError as http_err:
        try:            
            error_detail = sql_response.json().get('detail', str(http_err))
            st.error(f"❌ {error_detail}")
        except:
            st.error(f"Error HTTP {sql_response.status_code}")
        st.stop()


# Mostar resultados si existe una respuesta previa
if "last_response" in st.session_state:
    data = st.session_state["last_response"]
    contain_error = "error" in data['result']
    lock_to_save = contain_error
    with st.status("🧠 Detalle de resultados", expanded=False) as status:        
            
        tabs = st.tabs(["🧠 Reformulación", "📘 Contexto", "💻 SQL Generado",])            

        with tabs[0]:
            st.markdown(data['reformulation'])
        
        with tabs[1]:
            if data["flow"]:
                st.markdown(data['flow'])
            else:
                st.markdown(data["rag_context"])

        with tabs[2]:
            #st.text_area(data['sql'])
            edited_sql = st.text_area(
                "📝 Puedes editar el SQL si es necesario:", 
                value=data['sql'], 
                height=200
            )

            training_message = ""

            cols = st.columns([1, 1, 6])

            with cols[0]:
                if st.button("🐘", help="Ejecutar SQL", use_container_width=True):
                    payload ={"sql":edited_sql}
                    
                    try:
                        response = requests.post(API_SQL_EXECUTION, json=payload)
                        response.raise_for_status()
                        new_data = response.json()

                        contain_error = False
                        data['result'] = new_data["result"]
                        data['sql'] = new_data['sql']
                        edited_sql = new_data['sql']
                        st.session_state["last_response"] = data
                        st.toast("✅ Consulta ejecutada correctamente.")
                        lock_to_save = False

                    except requests.exceptions.HTTPError as http_err:
                        lock_to_save = True

                        try:
                            logger.error(response)
                            error_detail = response.json().get('detail', str(http_err))
                            data['result']['error']['message'] = error_detail

                        except:
                            data['result']['error']['message'] = f"Error HTTP {response.status_code}"                            

            with cols[1]:
                if st.button("💪", help='Entrenar el modelo', use_container_width=True, disabled=lock_to_save):
                    payload = {
                        "type": "sql",
                        "question": data['reformulation'],
                        "content": edited_sql
                    }
                    
                    try:
                        response = requests.post(API_SQL_TRAINING, json=payload)
                        response.raise_for_status()
                        training_message = "✅ Entrenamiento exitoso. El agente ha aprendido esta respuesta."
                        logger.info(f"✅ Entrenamiento exitoso. El agente ha aprendido esta respuesta.", exc_info=True)
                    
                    except Exception as e:
                        training_message = "❌ Error al guardar la respuesta."
                        logger.error(f"❌ Fallo al entrenar con SQL aprobado\n{e}", exc_info=True)

            if training_message:
                st.toast(training_message)

    with st.container(border=True, key='rs'):
        # Resultado fuera del status        
        if contain_error:
                message_placeholder = st.empty()  # Espacio reservado para el error
                message_placeholder.error(f"❌ {data['result']['error']['message']}")            
                logger.error(f"❌ Error al ejecutar el SQL\n{data['result']}", exc_info=True) 
                time.sleep(5)        
                message_placeholder.empty()            
        else:
            st.markdown("##### 📊 Resultados")
            df = pd.DataFrame(data['result']["rows"], columns=data['result']["columns"])
            st.dataframe(df, use_container_width=True)


st.divider()
st.caption(f" 🧠 _El **Agente SQL** puede cometer errores. El modelo utiliza datos de **{dominio}** para responder tus preguntas._")
st.caption(" 👨🏻‍💻 Powered by **IE team** - Grupo Reyma 2025")
