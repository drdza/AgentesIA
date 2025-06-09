# pages/eventos.py

import streamlit as st
import pandas as pd
import os
import json

st.set_page_config(page_title="Ejemplos Ejecutados", layout="wide")
st.title("📊 Resultados Fallidos del Agente SQL")

# Ruta del historial
LOG_PATH = "outputs/ptuning_failed_cases.jsonl"

def cargar_eventos():
    eventos = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    eventos.append(json.loads(line.strip()))
                except:
                    continue
    return eventos

# Cargar eventos
eventos = cargar_eventos()
# print(eventos)

if not eventos:
    st.warning("No se encontraron eventos registrados.")
else:
    df = pd.DataFrame(eventos)

    st.markdown("#### 🔍 Detalle de un Evento")

    opciones = df["original_question"].tolist()
    seleccionado = st.selectbox("Selecciona un evento para ver el detalle completo:", opciones)

    evento = df[df["original_question"] == seleccionado].iloc[0]

    tabs = st.tabs(["🧠 Reformulación", "📘 Flujo", "💻 SQL", "❌ Error"])
    with tabs[0]:
        st.markdown(evento["enhanced_question"])
    with tabs[1]:
        st.markdown(evento["flow"])
    with tabs[2]:
        st.code(evento["generated_sql"], language="sql")
    with tabs[3]:
        st.error(evento["error"])

    st.markdown("#### 🔍 Eventos")
    st.dataframe(
        df[["request_id", "original_question", "enhanced_question", "flow", "generated_sql", "error"]],
        use_container_width=True
    )