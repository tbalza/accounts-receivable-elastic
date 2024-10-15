import streamlit as st
import pandas as pd
from utils import found_transactions, ensure_data, load_data_from_sql, sync_transactions
from datetime import datetime, timedelta

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

# Initialize dates only if they are not already set
if 'start_date' not in st.session_state:
    st.session_state['start_date'] = datetime.now() - timedelta(days=30)
if 'end_date' not in st.session_state:
    st.session_state['end_date'] = datetime.now()

def page1():
    st.title("Bank API")

    ensure_data('page1')

    # Set up columns for date inputs and button
    c1, c2, c3 = st.columns([1, 1, 8], gap="small", vertical_alignment="bottom")
    with c1:
        start_date = st.date_input("Start Date", value=st.session_state.get('start_date', pd.Timestamp.today()), key="start_date", format="MM/DD/YYYY")
    with c2:
        end_date = st.date_input("End Date", value=st.session_state.get('end_date', pd.Timestamp.today()), key="end_date", format="MM/DD/YYYY")
    with c3:
        if st.button("Fetch Transactions"):
            transactions = found_transactions(start_date, end_date)
            sync_transactions(transactions)
            df_bank = load_data_from_sql('bank')
            st.session_state['df_bank'] = df_bank  # Update the cached dataframe

    df_bank = st.session_state['df_bank']
    df_bank.fillna(value="", inplace=True)  # Handling NaN values

    # Convert dates to datetime if not already
    df_bank['date'] = pd.to_datetime(df_bank['date']).dt.strftime('%m/%d/%Y')
    df_bank['bank_sync_date'] = pd.to_datetime(df_bank['bank_sync_date']).dt.strftime('%m/%d/%Y')

    # Filter DataFrame by date range
    df_bank_filtered = df_bank[
        (pd.to_datetime(df_bank['date'], format='%m/%d/%Y') >= pd.to_datetime(start_date)) &
        (pd.to_datetime(df_bank['date'], format='%m/%d/%Y') <= pd.to_datetime(end_date))
    ]

    # Define columns to display and sort by date
    columns = ['id', 'date', 'type', 'sender', 'description', 'amount', 'bank_sync_date']
    df_bank_filtered = df_bank_filtered[columns].sort_values(by='date', ascending=False)

    # Highlight newly synced bank entries
    def highlight_rows(s):
        # Format today's date as a string to match the format in 'bank_sync_date'
        today_str = datetime.now().strftime('%m/%d/%Y')
        # Check if 'bank_sync_date' is not empty and matches today's date
        if s['bank_sync_date'] and s['bank_sync_date'] == today_str:
            return ['background-color: #d2f4ea'] * len(s)
        # Return no styling if the date is not today or 'bank_sync_date' is empty
        return [''] * len(s)

    df_bank_styled = df_bank_filtered.style.apply(highlight_rows, axis=1)

    # Display styled DataFrame
    st.dataframe(df_bank_styled, width=900, hide_index=True, column_config={"id": st.column_config.NumberColumn(format="%f")})

    # Display logs
    if 'logs' in st.session_state:
        st.text_area("Logs", value="\n".join(reversed(st.session_state['logs'])), height=200)

page1()