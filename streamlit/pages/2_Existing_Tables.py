import streamlit as st
import sys
import os
sys.path.append(os.path.abspath('..'))
from utils import load_data_from_sql, log, ensure_data

# Set the Streamlit page configuration with a custom icon
st.set_page_config(
    page_title="AR Automation",
    page_icon="https://fonts.gstatic.com/s/i/materialicons/assessment/v12/24px.svg",  # Material Icon
    layout="wide",
)
with st.sidebar:
    st.page_link("Bank_API.py", label="Bank API", icon=":material/account_balance:")
    st.page_link("pages/2_Existing_Tables.py", label="Existing Tables", icon=":material/database:")
    st.page_link("pages/3_Combined_Clients.py", label="Combined Clients", icon=":material/person:")
    st.page_link("pages/4_Match_ClientID.py", label="Match ClientID", icon=":material/join_inner:")
    st.page_link("pages/5_Sync_ERP.py", label="Sync ERP", icon=":material/sync:")
    st.page_link("pages/6_Search.py", label="Search", icon=":material/search:")

def page2():
    st.title("Client and Student Data")
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'df_client' not in st.session_state or 'df_student' not in st.session_state:
        st.session_state.df_client = load_data_from_sql('client')
        st.session_state.df_student = load_data_from_sql('student')
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Client Data")
        st.dataframe(st.session_state.df_client,hide_index=True,column_config={"client id": st.column_config.NumberColumn(format="%f")})
    with col2:
        st.subheader("Student Data")
        st.dataframe(st.session_state.df_student,hide_index=True,column_config={"student id": st.column_config.NumberColumn(format="%f")})
    st.text_area("Logs", value="\n".join(reversed(st.session_state['logs'])), height=200)
    if st.button("Refresh Data"):
        st.session_state.df_client = load_data_from_sql('client')
        st.session_state.df_student = load_data_from_sql('student')

page2()
