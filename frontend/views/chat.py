
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
            timeout=60,
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
    print(f"Process Backend Response:\n{response}")
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
            "avatar": "🤖"
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
            "avatar": "🤖"
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
        with st.chat_message(message["role"], avatar=message.get("avatar", "🤖")):

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

def handle_chat():
    caption_placeholder = st.empty()
    caption_placeholder.caption(
        f"¡Hola {st.session_state.user_avatar} {st.session_state.user_name}!, bienvenid@ al Agente SQL"
    )

    # Inicializar variables de sesión si no existen
    st.session_state.setdefault("messages", [
        {
            "role": "assistant",
            "content": "Pregúntame y responderé con un query en SQL, te presentaré los resultados y algo de contexto.",
            "avatar": "🤖"
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
            #print(f"raw_response:\n{raw_response}")
            st.session_state.messages.append(message)

    # Renderizar historial completo
    render_message_history()    

def main():
    st.set_page_config(page_title="Agente SQL")    
    st.title("🤖 Agente SQL")
    st.session_state.setdefault("user_avatar", "🧑🏻")
    st.session_state.setdefault("user_name", "Humano")
    st.session_state.setdefault("dominio", "tickets")    
    handle_chat()


## Arranque de la app
main()
