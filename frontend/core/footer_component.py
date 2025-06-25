# footer_component.py
import streamlit as st
from htbuilder import HtmlElement, div, p, br, hr, styles
from htbuilder.units import percent, px


def layout(*args):
    style = """
    <style>
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
      .stApp { bottom: 105px; }
    </style>
    """

    style_div = styles(
        position="fixed",
        left=0,
        bottom=0,
        margin=px(0, 0, 0, 0),
        width=percent(100),
        color="black",
        text_align="center",
        height="auto",
        opacity=1,
        background="#f7f7f7",
        padding=px(10),
        font_size="14px",
        z_index=9999
    )

    style_hr = styles(
        display="block",
        margin=px(5, 5, "auto", "auto"),
        border_style="inset",
        border_width=px(1)
    )

    body = p()
    foot = div(
        style=style_div
    )(
        hr(style=style_hr),
        body
    )

    st.markdown(style, unsafe_allow_html=True)

    for arg in args:
        body(arg)

    st.markdown(str(foot), unsafe_allow_html=True)


def footer():
    domain = st.session_state.get("dominio", "tu sistema de datos")

    layout(
        "💬 El ", "Agente SQL", " puede cometer errores. Usa información de ",
        domain, " para responder tus preguntas.",
        br(),
        "👨🏻‍💻 Powered by ", "IE team – Grupo Reyma 2025"
    )
