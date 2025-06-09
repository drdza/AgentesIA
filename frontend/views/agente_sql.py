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
from shared.utils import load_prompt_template, load_config

CONFIG_JSON = load_config()
API_ENDPOINTS_BASE = CONFIG_JSON['api_endpoints_base']
API_SQL_GENERATION = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['generate_sql']
API_SQL_TRAINING = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['training']
API_SQL_EXECUTION = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['execute_sql']


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/app_debug.log', encoding='utf-8')],
    encoding='utf-8',
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Agente SQL")

def load_init_prompts(domain: str):
    if 'prompts' not in st.session_state:
        st.session_state.prompts = {
            'enhancer': load_prompt_template(domain=domain, template_name="question_enhancer.txt"),
            'flow': load_prompt_template(domain=domain, template_name="flow_generator_prompt.txt"),
            'sql': load_prompt_template(domain=domain, template_name="system_context.txt")
        }


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
    load_init_prompts(dominio)

    try:
        sql_response = requests.post(API_SQL_GENERATION,json={"question": pregunta_usuario, "domain": dominio})
        sql_response.raise_for_status()
        data = sql_response.json()
        st.session_state["last_response"] = data
    except Exception as e:
        st.error("❌ Error al generar SQL.")
        logger.error(f"Error al consultar el backend: {e}", exc_info=True)
        st.stop()

# Mostar resultados si existe una respuesta previa
if "last_response" in st.session_state:
    data = st.session_state["last_response"]
    contain_error = "error" in data['result']
    lock_to_save = False
    with st.status("🧠 Preparando resultados...", expanded=True) as status:        
            
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
                        lock_to_save = not new_data['success']
                        if new_data["success"]:                            
                            data['result'] = new_data["result"]
                            data['sql'] = edited_sql
                            st.session_state["last_response"] = data
                        else:
                            sql_text = st.toast("No pudimos procesar tu SQL.", icon='⚠️')
                            time.sleep(3)
                            sql_text.toast(f"{new_data['result']}")
                    except Exception as e:
                        lock_to_save = True
                        logger.error(f"❌ Fallo al ejecutar el SQL.\n{e}", exc_info=True)                    
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
                        logger.error(f"✅ Entrenamiento exitoso. El agente ha aprendido esta respuesta.", exc_info=True)
                    except Exception as e:
                        training_message = "❌ Error al guardar la respuesta."
                        logger.error(f"❌ Fallo al entrenar con SQL aprobado\n{e}", exc_info=True)
            if training_message:
                st.toast(training_message)

        # Resultado fuera del status        
    if contain_error:                    
            error_html = """
            <div style="border:1px,solid,white;border-radius:5px;margin-bottom:15px;background-color:rgba(255, 43, 43, 0.09);padding:15px">
                <div style="color: rgb(123 0 0 / 69%);font-weight: bold;">
                ❌ No pudimos procesar tu consulta.
                </div>
                <div style="margin-top: 10px;color: #7b0000;">
                Lamentamos el inconveniente. Se ha notificado al equipo técnico sobre este evento.
                </div>
            </div>
            """
            st.markdown(error_html, unsafe_allow_html=True)
            
            st.error(f"❌ Error al ejecutar SQL: {data['result']['error']}")

            #st.info("💡 Le sugerimos cambiar el enfoque de la pregunta y volverlo a intentar.")            
            logger.error(f"❌ Error al ejecutar el SQL\n{data['result']}", exc_info=True)             
    else:
        st.markdown("#### 📊 Resultados")
        df = pd.DataFrame(data['result']["rows"], columns=data['result']["columns"])
        st.dataframe(df, use_container_width=True)


st.divider()
st.caption(f" 🧠 **InnovAI** puede cometer errores. El modelo utiliza datos de **{dominio}** para responder tus preguntas.")
st.caption(" 👨🏻‍💻 Desarrollado por el equipo de IE – Grupo Reyma")

