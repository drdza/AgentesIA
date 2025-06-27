import streamlit as st

st.set_page_config(page_title="Sobre AltheIA – Tickets", page_icon="🧬")

st.markdown("""
<style>
.justify-content {
    text-align: justify;
    text-justify: inter-word;
}

.info-message {
    background-color: #e8f1fb; 
    color: #0f4c81;            
    border-left: 6px solid #4c96e0;
    padding: 10px 16px;
    border-radius: 6px;
    font-size: 0.95rem;
}

.contact-banner {
    background-color: #e7f5ec;
    color: #1b4332;
    border-left: 6px solid #95d5b2;
    padding: 12px 20px;
    border-radius: 6px;
    margin-top: 1.5rem;
    font-size: 0.95rem;
}

</style>
""", unsafe_allow_html=True)



st.markdown("## 🧬 ¿Cómo fue desarrollado AltheIA?")
st.markdown("Un vistazo técnico y humano detrás del primer agente especializado en consultas inteligentes sobre tickets.")

st.markdown("---")

st.markdown("""
<div class='justify-content'>
            
### 🎯 Objetivo

Desarrollar un agente que permita a cualquier persona del área de Innovación & Negocios consultar información del sistema de 
tickets de manera sencilla, utilizando lenguaje natural, sin necesidad de saber SQL ni depender de reportes técnicos.

</div>            
""", unsafe_allow_html=True)

st.markdown("""
<div class='justify-content'>
            
### 🧰 Tecnologías Clave

Este agente combina tecnologías de código abierto con infraestructura on-premise:

- 🧠 **Mistral 7B Instruct** como modelo de lenguaje.
- ⚡ **TGI de Hugging Face** como motor de inferencia.
- 📚 **Milvus + embeddings semánticos** para contextualización técnica.
- 🔄 **LangGraph** para orquestar pasos como reformulación y generación de SQL.
- 🚀 **FastAPI + PostgreSQL** como backend y fuente de datos.
- 🐍 **Python + Streamlit**como interfaz interactiva, ligera y fácil de mantener.
            
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='justify-content'>

### 🔄 ¿Cómo funciona?

1. El usuario escribe una pregunta, por ejemplo:  
   _“¿Cuántos tickets están en proceso este mes?”_

2. El modelo interpreta la intención e inicia un proceso de interacción entre nodos de servicio.

3. A través de **LangGraph**, cada paso del proceso es orquestado como un nodo:  
    - **Nodo 1**: Reformulación natural de la pregunta del usuario (LLM).
    - **Nodo 2**: Generación de flujo técnico o Recuperación de Contexto (Vectorstore)
    - **Nodo 3**: Generación y validación del SQL (LLM).

4. Se devuelven los resultados y se visualizan en forma de KPIs, tablas o gráficas.

5. El agente entrega un resumen visual + contexto + consulta generada.
            
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='justify-content'>
            
### 👨‍💻 Equipo de Desarrollo
            
Este agente fue desarrollado por el equipo de **Inteligencia Empresarial**, en colaboración con el área de **Servidores y Plataformas**, como parte del proyecto de habilitación del entorno técnico necesario para su operación, incluyendo la configuración de GPUs, el sistema operativo y los contenedores Docker requeridos.

La **Dirección de Innovación & Negocios** jugó un papel clave al apostar por esta iniciativa e invertir en las herramientas tecnológicas necesarias para su implementación.

</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='justify-content'>

### 🚧 Estado actual

**AltheIA – Tickets** se encuentra en versión **prototipo (v1.0)**. Actualmente responde a preguntas sobre:

- Tickets abiertos, en proceso o fuera de tiempo.
- Métricas por área o departamento.
- Comparativas mes a mes o año contra año.
- Tendencias básicas de atención o saturación.

⚠️ **Limitaciones actuales**:

- Puede no interpretar bien preguntas muy abiertas o ambiguas.
- No cubre aún métricas de satisfacción o complejidad del ticket.
- La precisión depende de los campos disponibles en la base de datos.
            
</div>
""", unsafe_allow_html=True)

st.markdown("""
### 🔮 Lo que viene

- Inclusión de nuevos dominios: **solicitudes de servicio**, **proyectos wrike**, **solicitudes de equipos de cómputo**, etc.
- Macroagente bajo arquitectura RAG e implementación de modelos LLM con más potencia.
- Mejora de respuestas tipo “porcentaje”, “tendencia”, “desviación”.
- Validación semántica con contexto previo del usuario.
- Integración con interfaces externas como **business suite**, **whatsApp** o **innovapp**.
- Dashboard de monitoreo de uso, feedback y rendimiento.

---
""", unsafe_allow_html=True)

### 🌟 ¿Por qué se llama AltheIA?
st.markdown(
"""
<div class='justify-content'>

### 📖 El origen

**AltheIA** nació de una combinación de inspiración y casualidad. En un principio, partimos de la palabra griega **Aletheia**, que significa *“verdad revelada”* — un concepto que resonaba con nuestra visión de una inteligencia artificial que no solo responde, sino que **descubre, aclara y revela**.

**AltheIA** empezó a sonar como un acrónimo no oficial de *“All-the-IA”* —  
> “**Toda la inteligencia artificial concentrada en el negocio**”.

Este nuevo nombre cobró un nuevo sentido: no solo evoca verdad y profundidad, sino también un enfoque integrador, elegante e innovador.

<div class='info-message'>
<strong>AltheIA no es solo un asistente:</strong> es la puerta a una nueva forma de pensar los datos, 
las decisiones y el conocimiento en la organización.
</div>

</div>
""", unsafe_allow_html=True)

st.divider()

st.markdown("""
<div class='contact-banner'>            

<strong>¿Tienes ideas, dudas o sugerencias?</strong>
<p>Escríbenos a <a href='mailto:inteligencia.empresarial@reyma.com.mx'>inteligencia.empresarial@reyma.com.mx</a> o acercate con la coordinación de IE, será un placer conectar contigo.</p>

</div>
"""      
, unsafe_allow_html=True)
