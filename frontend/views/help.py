import streamlit as st

st.markdown("""
<style>
.guia-container {
    background-color: ##fafafa63;
    padding: 1.2em;
    border-left: 5px solid #02303c;
    border-radius: 6px;
    font-family: sans-serif;
    font-size: 0.95rem;
}
.guia-container ul {
    margin-top: 0.2rem;
}
.guia-container li {
    margin-bottom: 0.3rem;
}
.guia-container a {
    color: #4F8BF9;
    text-decoration: none;
}
.guia-container a:hover {
    text-decoration: underline;
}
</style>

<div class='guia-container'>

### 🧭 Guía rápida de uso

Este asistente responde **consultas analíticas sobre tickets**. Asegúrate de que tu pregunta tenga ese enfoque.

---

#### ✅ Ejemplos válidos:
<ul>
<li>¿Cuántos tickets están abiertos este mes?</li>
<li>¿Cuántos tickets cerró el área de Soporte?</li>
<li>Entrégame las estadísticas de los tickets del mes de Junio 2025</li>
<li>¿Cuántos tickets tiene en proceso el colaborador Daniel Ibarra?</li>
</ul>

#### ❌ Ejemplos no válidos:
<ul>
<li>¿Cómo se genera un ticket?</li>
<li>¿Qué es un ticket?</li>
<li>¿Dónde reporto un problema?</li>
</ul>

---

👉 Si tu pregunta no se puede responder con datos, recibirás una explicación generada con IA.

📖 Consulta más en: <a href='http://localhost:8501/about_altheia#como-funciona' target='_blank'>Guía completa de ayuda</a>

</div>
""", unsafe_allow_html=True)
