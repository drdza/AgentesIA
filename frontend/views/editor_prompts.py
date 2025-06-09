# pages/editor_prompts.py

import os
import streamlit as st
from shared.utils import load_prompt_template, load_config

# Config
st.set_page_config(page_title="Editar Prompts", layout="wide")
st.title("🛠️ Editor de Prompts")

config = load_config()
domain = st.selectbox("Temas disponibles", config['temas'])
prompt_keys = ['enhancer', 'flow', 'sql']

def init_prompts():    
    if 'prompts' not in st.session_state:
        st.session_state.prompts = {
            'enhancer': load_prompt_template(domain=domain, template_name="question_enhancer.txt"),
            'flow': load_prompt_template(domain=domain, template_name="flow_generator_prompt.txt"),
            'sql': load_prompt_template(domain=domain, template_name="system_context.txt")
        }
    
    # Inicializar estados de edición
    for k in prompt_keys:
        if f"edit_mode_{k}" not in st.session_state:
            st.session_state[f"edit_mode_{k}"] = False
    


prompt_titles = {
    'enhancer': "✏️ Prompt para Reformulación de Preguntas",
    'flow': "⚙️ Prompt para Generación del Flujo Técnico",
    'sql': "💻 Prompt para Generación del SQL"
}

prompt_files = {
    'enhancer': "question_enhancer.txt",
    'flow': "flow_generator_prompt.txt",
    'sql': "system_context.txt"
}

# Vista por tabs para cada tipo de prompt
tabs = st.tabs([prompt_titles[k] for k in prompt_keys])
init_prompts()

for i, key in enumerate(prompt_keys):
    with tabs[i]:
        st.subheader(prompt_titles[key])

        # Mostrar markdown o editor según estado
        if not st.session_state[f"edit_mode_{key}"]:
            st.markdown(f"{st.session_state.prompts[key]}")
        else:
            st.session_state.prompts[key] = st.text_area(
                label="Editar prompt:",
                value=st.session_state.prompts[key],
                height=400,
                key=f"textarea_{key}"
            )

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if not st.session_state[f"edit_mode_{key}"]:
                if st.button(f"✏️ Editar {key}", key=f"edit_{key}"):
                    st.session_state[f"edit_mode_{key}"] = True
                    st.rerun()
            else:
                if st.button(f"❌ Cancelar {key}", key=f"cancel_{key}"):
                    st.session_state[f"edit_mode_{key}"] = False
                    st.rerun()

        with col2:
            if st.session_state[f"edit_mode_{key}"]:
                if st.button(f"💾 Guardar {key}", key=f"save_{key}"):
                    with open(prompt_files[key], "w", encoding="utf-8") as f:
                        f.write(st.session_state.prompts[key])
                    st.success("✅ Prompt guardado.")
                    st.session_state[f"edit_mode_{key}"] = False
                    st.rerun()


        with col3:
            if st.button(f"🔄 Recuperar {key}", key=f"reset_{key}"):
                original = load_prompt_template(prompt_files[key])
                st.session_state.prompts[key] = original
                st.success("Prompt restaurado desde archivo.")
                if st.session_state[f"edit_mode_{key}"]:
                    st.rerun()
