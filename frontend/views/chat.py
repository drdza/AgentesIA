
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

st.set_page_config(page_title="Agente SQL")

def main():    

    st.title("🤖 Chatbot")

    st.session_state.user_avatar = "🧑🏻"
    st.session_state.user_name = "Humano"
    st.session_state.dominio = "tickets"
    
    handle_chat()

    # caption_placeholder = st.empty()
    # form_placeholder = st.empty() 

    # # Initialize the user name if it doesn't exist
    # if "user_name" not in st.session_state or not st.session_state.user_name:
    #     with form_placeholder.form(key='user_form'):
    #         caption_placeholder.caption("🚀 A streamlit chatbot powered by IE-Team")
    #         user_name = st.text_input("Please enter your name:")
    #         user_avatar = st.radio("Please choose an avatar:", ["🐼", "🐶", "🐱", "🦊","🦄","🌸","⭐","🌈","❄️","👻","👾"], 
    #                                 index=0,
    #                                 horizontal=True,)
    #         submit_button = st.form_submit_button(label='Start Chat')
    #     if submit_button and user_name:
    #         st.session_state.user_name = user_name
    #         st.session_state.user_avatar = user_avatar
    #         caption_placeholder.empty()
    #         form_placeholder.empty()  # Elimina el formulario de la interfaz
    #         handle_chat()
    # else:
    #     handle_chat()

def suggest_visualization(df: pd.DataFrame) -> str:
    if df.shape[0] == 1 and df.shape[1] <= 3:
        return "kpi"
    elif "fecha" in df.columns[0].lower() or "mes" in df.columns[0].lower():
        return "line_chart"
    elif df.shape[0] <= 20 and df.shape[1] <= 5:
        return "bar_chart"
    else:
        return "dataframe"



def handle_chat():
    caption_placeholder = st.empty()
    caption_placeholder.caption(f"¡Hola {st.session_state.user_avatar} {st.session_state.user_name}!, bienvenid@ al Agente SQL")
    
    if "explanation_status" not in st.session_state:
        st.session_state.explanation_status = False

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", 
             "content": "Pregúntame y responderé con un query en SQL, te presentaré los resultados y algo de contexto.", 
             "avatar": "🤖"}
        ]

    if prompt := st.chat_input("¿Cuál es tu pregunta?"): 
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt, 
            "avatar": st.session_state.user_avatar
        })

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"], avatar=message.get("avatar", "🤖")):
            if isinstance(message["content"], dict) and message["role"] == "assistant":
                df = pd.DataFrame(
                    message["content"]["result"]["rows"],
                    columns=message["content"]["result"]["columns"]
                )

                with st.expander("🧠 Detalles del agente", expanded=False):
                    tabs = st.tabs(["🧠 Reformulación", "📘 Contexto", "💻 SQL Generado",]) 
                    with tabs[0]:
                        st.markdown(message['content']['reformulation'])

                    with tabs[1]:
                        if message['content']['flow']:
                            st.markdown(message['content']['flow'])
                        else:
                            st.markdown(message['content']['context'])

                    with tabs[2]:
                        st.code(message['content']['sql'], language="sql", line_numbers=True)   

                viz_options = ["DataFrame", "Barras", "Lineas", "KPIs"]
                selected_viz = st.radio(
                    "🔍 Cómo deseas visualizar los datos:",
                    viz_options,
                    index=viz_options.index(message["content"].get("viz_type", "dataframe")),
                    key=f"viz_selector_{i}",
                    horizontal=True
                )

                # Actualiza el tipo de visualización guardado
                st.session_state.messages[i]["content"]["viz_type"] = selected_viz                
                # Render según el tipo seleccionado
                st.markdown("### 📊 Resultados")
                chart_placeholder = st.empty()


                if selected_viz == "DataFrame":
                    chart_placeholder.dataframe(df, use_container_width=True)
                elif selected_viz == "Barras":
                    numeric_cols = df.select_dtypes(include=["number"]).columns
                    chart_placeholder.bar_chart(df.set_index(df.columns[0]))
                elif selected_viz == "Lineas":
                    chart_placeholder.line_chart(df.set_index(df.columns[0]))
                elif selected_viz == "KPIs":
                    numeric_cols = df.select_dtypes(include=["number"]).columns                    
                    kpi_values = df.iloc[0][numeric_cols].round(2) if len(df) > 0 else []
                    cols = st.columns(len(kpi_values)) if len(kpi_values) > 0 else []                    
                    for i, col in enumerate(numeric_cols):
                        with cols[i]:
                            st.metric(label=col, value=kpi_values[col])

            else:
                st.write(message["content"])



    if st.session_state.messages[-1]["role"] != "assistant":
        with st.spinner("Analizando..."):
            last_question = st.session_state.messages[-1]["content"]
            try:
                response = requests.post(API_SQL_GENERATION, json={"question": last_question, "domain": st.session_state.dominio})
                response.raise_for_status()
                data = response.json()

                sql_response = data.get("sql")
                reformulation_response = data.get("reformulation")
                flow_response = data.get("flow")
                result_response = data.get("result")
                context_response = data.get("rag_context", "")
                message_response = "Aquí los resultados a tu pregunta:"

            except requests.exceptions.HTTPError:
                sql_response = None
                message_response = "No pude procesar tu pregunta. Intenta replantearla."
        
        with st.chat_message("assistant", avatar="🤖"):

            if sql_response:
                st.markdown(f"**{message_response}**")

                with st.expander("🧠 Detalles del agente", expanded=False):
                    tabs = st.tabs(["🧠 Reformulación", "📘 Contexto", "💻 SQL Generado",]) 
                    with tabs[0]:
                        st.markdown(reformulation_response)

                    with tabs[1]:
                        if flow_response:
                            st.markdown(flow_response)
                        else:
                            st.markdown(context_response)

                    with tabs[2]:
                        st.code(sql_response, language="sql", line_numbers=True)                

                viz_options = ["DataFrame", "Barras", "Lineas", "KPIs"]
                default_viz = "DataFrame"

                selected_viz = st.radio(
                    "🔍 Cómo deseas visualizar los datos:",
                    viz_options,
                    index=viz_options.index(default_viz),
                    key="viz_selector_current",
                    horizontal=True
                )
                                                                
                df = pd.DataFrame(result_response["rows"], columns=result_response["columns"])

                st.markdown("##### 📊 Resultados")

                if selected_viz == "DataFrame":
                    st.dataframe(df, use_container_width=True)
                elif selected_viz == "Barras":
                    st.bar_chart(df.set_index(df.columns[0]))
                elif selected_viz == "Lineas":
                    st.line_chart(df.set_index(df.columns[0]))
                elif selected_viz == "KPIs":
                    numeric_cols = df.select_dtypes(include=["number"]).columns                    
                    kpi_values = df.iloc[0][numeric_cols].round(2) if len(df) > 0 else []
                    cols = st.columns(len(kpi_values)) if len(kpi_values) > 0 else []                    
                    for i, col in enumerate(numeric_cols):
                        with cols[i]:
                            st.metric(label=col, value=kpi_values[col])

                message = {
                    "role": "assistant",
                    "content": {
                        "sql": sql_response,
                        "reformulation": reformulation_response,
                        "flow": flow_response,
                        "context": context_response,
                        "result": result_response,
                        "viz_type":"DataFrame" 
                    },
                    "avatar": "🤖"
                }                    

            else:
                st.error(message_response)

                message = {
                    "role": "assistant",
                    "content": {
                        "sql": None,
                        "reformulation": None,
                        "flow": None,
                        "context": None,
                        "result": None,
                        "viz_type":None,
                        "error": "⚠️ No se pudo procesar tu pregunta. Intenta replantearla o contacta a soporte."
                    },
                    "avatar": "🤖"
                }

        st.session_state.messages.append(message)


    if st.session_state.explanation_status:
        if st.button('¿Deseas una explicación de la consulta?'):
            with st.spinner("Analizando..."):
                # ask the model for an explanation of the last query
                #explanation = model.explain(st.session_state.last_message)
                
                # print the explanation as a new message from the assistant
                explanation_message_response = st.chat_message("assistant", avatar="🤖")
                #explanation_message_response.write(explanation)

                # add explanation to message history
                #explanation_message = {"role": "assistant", "content": explanation}
                #st.session_state.messages.append(explanation_message)



if __name__ == "__page__":
    main()