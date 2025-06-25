# main.py
import streamlit as st

pages=[
    st.Page("views/entrenamiento.py", title="Training", icon='💾'),
]

pg=st.navigation(pages, position="top")
pg.run()