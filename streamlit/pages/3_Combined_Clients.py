import streamlit as st
import sys
import os
sys.path.append(os.path.abspath('..'))
from utils import ensure_data, log, combine_clients

# Set the Streamlit page configuration with a custom icon
st.set_page_config(
    page_title="AR Automation",
    page_icon="https://fonts.gstatic.com/s/i/materialicons/assessment/v12/24px.svg",
    layout="wide",
)
with st.sidebar:
    st.page_link("Bank_API.py", label="Bank API", icon=":material/account_balance:")
    st.page_link("pages/2_Existing_Tables.py", label="Existing Tables", icon=":material/database:")
    st.page_link("pages/3_Combined_Clients.py", label="Combined Clients", icon=":material/person:")
    st.page_link("pages/4_Match_ClientID.py", label="Match ClientID", icon=":material/join_inner:")
    st.page_link("pages/5_Sync_ERP.py", label="Sync ERP", icon=":material/sync:")
    st.page_link("pages/6_Search.py", label="Search", icon=":material/search:")

def page3():
    st.title("Combined Client Data")
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    ensure_data('page3')
    st.dataframe(st.session_state.df_client_combined,hide_index=True,column_config={"client id": st.column_config.NumberColumn(format="%f")})
    st.text_area("Logs", value="\n".join(reversed(st.session_state['logs'])), height=200)
    if st.button("Update and Upload Data"):
        combine_clients()

page3()