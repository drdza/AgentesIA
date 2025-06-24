# main.py
import streamlit as st


pages = [
    st.Page("views/chat.py", title="Agente SQL", icon="🤖")
]

pg= st.navigation(pages, position="top")
pg.run()