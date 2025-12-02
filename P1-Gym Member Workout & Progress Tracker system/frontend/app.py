import streamlit as st
from app_ui import show_app_ui
from app_analytics_ui import show_analytics_ui

st.set_page_config(layout='wide', page_title='Gym Progress Tracker')

API = "http://localhost:8000"

if 'API' not in st.session_state:
    st.session_state['API'] = API

st.title('Gym Member Workout & Progress Tracker system ')

menu = st.sidebar.selectbox('Menu', ['Home / UI', 'Analytics', 'About'])

if menu == 'Home / UI':
    show_app_ui()
elif menu == 'Analytics':
    show_analytics_ui()
else:
    st.markdown('### About')
    st.markdown('This system helps you to track your weekly progress and helps gym owners to track their clinet records')