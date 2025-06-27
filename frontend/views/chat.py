
import sys
import os
import requests
import logging
import streamlit as st
import pandas as pd
from traceback import format_exc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import load_config
from core.visualizations import render_visual_response, render_error_with_agent_context
from core.footer_component import footer

CONFIG_JSON = load_config()
API_ENDPOINTS_BASE = CONFIG_JSON['api_endpoints_base']
API_SQL_GENERATION = API_ENDPOINTS_BASE + CONFIG_JSON['api_endpoints']['generate_sql']


def fetch_sql_response(question: str, domain: str) -> dict:
    """
    Consulta el backend para generar SQL a partir de una pregunta.
    Devuelve un diccionario estandarizado, ya sea exitoso o con error.
    """
    try:
        response = requests.post(
            API_SQL_GENERATION,
            json={"question": question, "domain": domain},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        try:
            error_msg = response.json().get("detail", str(e))
        except Exception:
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

def process_backend_response(response: dict) -> dict:    
    if "sql" in response and "result" in response:
        return {
            "role": "assistant",
            "content": {
                "sql": response.get("sql"),
                "reformulation": response.get("reformulation"),
                "flow": response.get("flow"),
                "context": response.get("rag_context", ""),
                "result": response.get("result"),
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
                "viz_type": None,
                "error": response.get("error", "⚠️ Error desconocido. Intenta nuevamente.")
            },
            "avatar": st.session_state.assistant_avatar
        }

def _render_agent_details(data: dict):
    """Renderiza la respuesta: SQL, contexto, resultado y visualización."""    
    with st.expander("🧠 Detalles del agente", expanded=False):
        tabs = st.tabs(["🧠 Reformulación", "📘 Contexto", "💻 SQL Generado"])
        with tabs[0]:
            st.markdown(data.get("reformulation", ""))
        with tabs[1]:
            st.markdown(data.get("flow") or data.get("context", ""))
        with tabs[2]:
            st.code(data.get("sql", ""), language="sql", line_numbers=True)

def render_message_history():    
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"], avatar=message.get("avatar", "assistant_avatar")):

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
                else:
                    render_visual_response(content, i)
                
                # Mostrar detalles si existen
                _render_agent_details(content)
            # 🟡 Otros tipos de mensajes (usuario u otros)
            else:
                st.write(content)

def _handle_chat():    
    caption_placeholder = st.empty()
    caption_placeholder.markdown(
        f"""
        <div class="init-message">
            ¡Hola 🙋🏻‍♂️ {st.session_state.user_name}!
            Te doy la bienvenida a <strong>AltheIA – Tickets</strong>, 
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
            "content": "Pregúntame y responderé con un query en SQL, te presentaré los resultados y algo de contexto.",
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

        # Llamar backend
        with st.spinner("Analizando..."):
            raw_response = fetch_sql_response(prompt, st.session_state.dominio)
            message = process_backend_response(raw_response)
            st.session_state.messages.append(message)

    # Renderizar historial completo
    render_message_history()   

def _custom_agent():
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
    _custom_agent()
    st.title("AltheIA - Tickets")
    st.session_state.setdefault("assistant_avatar", "https://raw.githubusercontent.com/drdza/st-images/refs/heads/main/avatar/artificial-intelligence.png")
    st.session_state.setdefault("user_avatar", "https://raw.githubusercontent.com/drdza/st-images/refs/heads/main/avatar/user.png")
    st.session_state.setdefault("user_name", "InnovAmigo")
    st.session_state.setdefault("dominio", "tickets")    
    _handle_chat()
    

## Arranque de la app
main()
