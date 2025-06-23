# views/eventos.py

import streamlit as st
import pandas as pd
import os
import json
import logging
from datetime import date

st.set_page_config(page_title="Ejemplos Ejecutados", layout="wide")
st.title("📊 Resultados Fallidos del Agente SQL")

# Variables gloables
log_path = ""
tipo_evento = ""
fecha_seleccionada = date.today()

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/app_debug.log', encoding='utf-8')],
    encoding='utf-8',
)
logger = logging.getLogger(__name__)

def cargar_eventos(tipo_evento, fecha):
    if tipo_evento == "Correctos":
        log_path = f"outputs/success/ptuning_success_cases_{fecha.strftime('%Y%m%d')}.jsonl"
    else:
        log_path = f"outputs/fails/ptuning_fails_cases_{fecha.strftime('%Y%m%d')}.jsonl"

    eventos = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    eventos.append(json.loads(line.strip()))
                except:
                    continue

    st.session_state['eventos'] = eventos 
    return eventos, log_path

eventos =[]
if "eventos" not in st.session_state:
    st.session_state['eventos'] = eventos 

# Validar acceso de administrador
if "admin" not in st.session_state or not st.session_state.admin:
    st.warning("🔒 Acceso restringido. Introduce contraseña para continuar.")
    password = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if password == st.secrets["admin_password"]:  # o usa una constante
            st.session_state.admin = True
            st.success("✅ Acceso concedido")
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta")
    st.stop()


col1, col2, col4, col3 = st.columns([2,2,3,1])
with col1:
    # 📅 Selección de fecha
    fecha_seleccionada = st.date_input("Selecciona la fecha del log a consultar:", value=date.today())

with col2:
    tipo_evento = st.radio(
            "Tipo de evento",
            ["Correctos", "Fallidos"],
            horizontal=True
            )
with col3:
    st.metric(label="Eventos del día", value=len(st.session_state['eventos']) , border=True)

# Cargar eventos del archivo seleccionado
eventos, path = cargar_eventos(tipo_evento, fecha_seleccionada)


if not eventos:
    st.warning(f"No se encontraron eventos en `{path}`.")
else:
    df = pd.DataFrame(eventos)

    st.markdown("#### 🔍 Detalle de un Evento")

    opciones = df["original_question"].tolist()
    seleccionado = st.selectbox("Selecciona un evento para ver el detalle completo:", opciones)

    evento = df[df["original_question"] == seleccionado].iloc[0]
    tabs = st.tabs(["🧠 Reformulación", "📘 Flujo", "💻 SQL", "🌐 Metadata"])
    with tabs[0]:
        st.markdown(evento["enhanced_question"])
    with tabs[1]:
        st.markdown(evento["flow"])
    with tabs[2]:
        st.code(evento["generated_sql"], language="sql")
    with tabs[3]:
        if 'columns' in evento['result']:
            df_result = pd.DataFrame(evento["result"]["rows"], columns=evento["result"]["columns"])
            st.dataframe(df_result)
        elif 'error' in evento['result']:
            st.markdown("**El evento arrojó un error de tipo:** ")
            st.error(evento['result']['error'])
        else:
            st.markdown(evento["result"])    
        

    st.divider()

    with st.expander("#### 🔍 Detalle de eventos"):
        st.dataframe(
            df[["request_id", "original_question", "enhanced_question", "flow", "generated_sql", "result"]],
            use_container_width=False
        )