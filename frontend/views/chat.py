
import sys
import os
import requests
import logging
import streamlit as st
import pandas as pd
from traceback import format_exc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import load_config, load_css_style
from core.visualizations import render_visual_response, render_error_with_agent_context, render_out_domain_agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Agrega un handler si no existe
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s]: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

CONFIG_JSON = load_config()
API_ENDPOINTS_BASE = CONFIG_JSON['api_endpoints_base']
API_SQL_GENERATION = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['generate_sql']

def _fetch_sql_response(domain: str, question: str, previous_question: str = None) -> dict:
    """
    Consulta el backend para generar SQL a partir de una pregunta.
    Devuelve un diccionario estandarizado, ya sea exitoso o con error.
    """
    payload = {
        "question": question,
        "previous_question": previous_question,
        "domain": domain
    }

    #logger.info(f"Payload: {payload}")

    try:
        response = requests.post(
            API_SQL_GENERATION,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()
        # logger.info(f"Response\n{response.json()}")
        return response.json()

    except requests.exceptions.HTTPError as e:
        try:
            logger.error(f"Error HTTP {response.status_code}: {response.json()}")
            error_msg = response.json().get("detail", str(e))
        except Exception:
            logger.error(f"Error HTTP {response.status_code}: {response.json()}")
            error_msg = str(e)
        return {
            "error": f"❌ Error HTTP {response.status_code}: {error_msg}"
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": f"❌ Error de conexión: {str(e)}"
        }

    except Exception as e:
        return {
            "error": f"❌ Error inesperado: {str(e)}"
        }

def _process_backend_response(response: dict) -> dict:    
    if "sql" in response and "result" in response:
        return {
            "role": "assistant",
            "content": {
                "sql": response.get("sql"),
                "reformulation": response.get("reformulation"),
                "flow": response.get("flow"),
                "context": response.get("rag_context", ""),
                "result": response.get("result"),
                "duration": response.get("duration_agent"),
                "narrative": response.get("narrative", ""),
                "viz_type": "DataFrame"
            },
            "avatar": st.session_state.assistant_avatar
        }
    else:
        return {
            "role": "assistant",
            "content": {
                "sql": None,
                "reformulation": None,
                "flow": None,
                "context": None,
                "result": None,
                "duration": None,
                "narrative": None,
                "viz_type": None,
                "error": response.get("error", "⚠️ Error desconocido. Intenta nuevamente.")
            },
            "avatar": st.session_state.assistant_avatar
        }

def _render_agent_details(data: dict):
    """Renderiza la respuesta: SQL, contexto, resultado y visualización."""     
    with st.expander("📖 Narrativa", expanded=False):
        st.markdown(data["narrative"])
    
    with st.expander("🧠 Detalles del agente", expanded=False):
        tabs = st.tabs(["🧠 Reformulación", "📘 Contexto", "💻 SQL Generado"])
        with tabs[0]:
            st.markdown(data.get("reformulation", ""))
        with tabs[1]:
            context = "\n\n ---".join(filter(None, [data.get("flow"), data.get("context")]))
            st.markdown(context)
        with tabs[2]:
            st.code(data.get("sql", ""), language="sql", line_numbers=True)

def _render_message_history():    
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"], avatar=message.get("avatar", "assistant_avatar")):
            show_details = True
            content = message.get("content")

            # 🔴 Caso 1: Error global (el endpoint ni respondió)
            if isinstance(content, dict) and content.get("error"):
                st.error(content["error"])
                continue

            # 🟢 Caso 2: Respuesta válida del agente
            if isinstance(content, dict) and message["role"] == "assistant":
                # Evaluar si hubo error en la ejecución del SQL
                result = content.get("result", {})
                if isinstance(result, dict) and "error" in result:                    
                    render_error_with_agent_context(content, i)
                elif isinstance(result, dict) and "out_domain" in result:
                    show_details = False
                    render_out_domain_agent(content, i)
                else:
                    render_visual_response(content, i)
                
                if show_details:
                    _render_agent_details(content)
            # 🟡 Otros tipos de mensajes (usuario u otros)
            else:
                st.write(content)

def _get_previous_user_question():
    user_messages = [
        msg["content"]
        for msg in reversed(st.session_state.messages)
        if msg["role"] == "user"
    ]
    return user_messages[1] if len(user_messages) > 1 else None


def _handle_chat():    
    caption_placeholder = st.empty()
    caption_placeholder.markdown(
        f"""
        <div class="init-message">
            ¡Hola 🙋🏻‍♂️!
            Te doy la bienvenida a <strong>AltheIA</strong>, 
            nuestro primer agente SQL con IA diseñado para ayudarte a consultar y entender nuestros datos.
        </div>        
        <div class='diss-message'>
            <strong>⚠️ Este agente está en fase de prueba.</strong> Por favor, revisa con cuidado los resultados antes de tomar decisiones.
        </div>        
        """
        , unsafe_allow_html=True
    )
    st.divider()


    # Inicializar variables de sesión si no existen
    st.session_state.setdefault("messages", [
        {
            "role": "assistant",
            "content": "Hazme una pregunta y generaré la consulta **SQL por ti**. Te mostraré los resultados y algo de contexto útil.",
            "avatar": st.session_state.assistant_avatar
        }
    ])
    st.session_state.setdefault("explanation_status", False)

    # Capturar nueva pregunta del usuario
    if prompt := st.chat_input("¿Cuál es tu pregunta?"):
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "avatar": st.session_state.user_avatar
        })

        previous_question = _get_previous_user_question()

        # Llamar backend
        with st.spinner("Analizando..."):
            raw_response = _fetch_sql_response(st.session_state.dominio,prompt, previous_question)
            message = _process_backend_response(raw_response)
            st.session_state.messages.append(message)

    # Renderizar historial completo
    _render_message_history()   


    st.markdown("""
        <style>
        
        .init-message {            
            color:#051e33;
            font-family: 'Segoe UI', sans-serif;
        }
        
        .diss-message {
            font-size: small;
            color:#6f7070;
            opacity: 0.7;            
            padding-top: 10px;            
            padding-bottom: 10px;
            font-family: 'Segoe UI', sans-serif;
        }
                
        /* Estilo para h1 */
        h1 {
            color: #051e33 !important;  /* Azul institucional */
            font-size: 2.3rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 1rem;
            font-family: 'Segoe UI', sans-serif;
        }
        
        /* Aplica sombra y fondo solo al asistente */
        div[data-testid="stChatMessage"]:has(img[alt="assistant avatar"]) {            
            background-color: rgba(255, 255, 255, 0.2);
            back
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0px 1px 5px rgba(128, 116, 168, 0.5);
        }

        /* Aplica sombra y fondo distinto al usuario (cuando NO es el asistente) */
        div[data-testid="stChatMessage"]:not(:has(img[alt="assistant avatar"])) {
            background-color: rgba(12, 54, 89, 0.1);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0px 1px 5px rgba(12, 54, 89, 0.2);
        }
                
        </style>
        """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="AltheIA SQL")        
    st.markdown(load_css_style("about_style.css"), unsafe_allow_html=True)   
    st.title("AltheIA")
    st.session_state.setdefault("assistant_avatar", "https://raw.githubusercontent.com/drdza/st-images/refs/heads/main/avatar/artificial-intelligence.png")
    st.session_state.setdefault("user_avatar", "https://raw.githubusercontent.com/drdza/st-images/refs/heads/main/avatar/user.png")
    st.session_state.setdefault("user_name", "InnovAmigo")
    st.session_state.setdefault("dominio", "tickets")    
    _handle_chat()
    

## Arranque de la app
main()
