import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.sidebar.subheader('Chart Options')
ticker = st.sidebar.text_input('Ticker', value = "AAPL")
theme = st.sidebar.selectbox('Theme', options = ['dark', 'light'])
fund_type = st.sidebar.selectbox('Fundamental Display', options = ['regular', 'compact'])
