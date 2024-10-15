import streamlit as st
import sys
import os
sys.path.append(os.path.abspath('..'))
from utils import search_index, ensure_data

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

def page6():
    st.title('Search')
    ensure_data('page6')
    search_index()  # All logic is encapsulated in this function

page6()