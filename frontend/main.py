# main.py
import streamlit as st


pages = [
    st.Page("views/chat.py", title="AltheIA SQL", icon="💬"),
    st.Page("views/about_altheia.py", title="About", icon="👩🏻‍💻"),
    st.Page("views/help.py", title="Help", icon="🚨")
]

pg= st.navigation(pages, position="top")
pg.run()