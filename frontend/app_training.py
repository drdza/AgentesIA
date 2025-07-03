# main.py
import streamlit as st

pages=[
    st.Page("views/training.py", title="Training", icon='💾'),
]

pg=st.navigation(pages, position="top")
pg.run()