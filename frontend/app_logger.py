# main.py
import streamlit as st

pages=[
    st.Page("views/training.py", title="Training", icon='💾'),
    st.Page("views/events.py", title="Events", icon='📝'),
]

pg=st.navigation(pages, position="top")
pg.run()