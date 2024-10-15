import streamlit as st
import sys
import os
sys.path.append(os.path.abspath('..'))
from utils import ensure_data, log, get_highest_relevance_clientid

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

def page4():
    st.title("Sync ERP")
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    ensure_data('page4')
    st.session_state.df_bank_matched = get_highest_relevance_clientid(st.session_state.df_bank_terms, 'es_client_combined')
    st.dataframe(st.session_state.df_bank_matched,hide_index=True)

    st.text("Pending implementation (rough draft):")

    code = '''
    import streamlit as st
    import sys
    import os
    sys.path.append(os.path.abspath('..'))
    from utils import ensure_data, log, get_highest_relevance_clientid, erp_sync

    # Using Pythonnet with the SAP B1 DI API (Data Interface Application Programming Interface) to insert data
    clr.AddReference('SAPbobsCOM')

    def insert_payments(df):
        # Logging setup
        log_file = "sap_b1_operations.log"

        # Log a message
        def log(message):
            with open(log_file, 'a') as f:
                f.write(f"{DateTime.Now}: {message}\\n")

        # Create company object
        company = clr.SAPbobsCOM.Company()

        # Set database connection properties (change accordingly)
        company.Server = "YOUR_SERVER"
        company.DbServerType = clr.SAPbobsCOM.BoDataServerTypes.dst_MSSQL2016
        company.CompanyDB = "YOUR_COMPANY_DB"
        company.UserName = "YOUR_USERNAME"
        company.Password = "YOUR_PASSWORD"
        company.language = clr.SAPbobsCOM.BoSuppLangs.ln_English

        # Connect to SAP B1
        ret = company.Connect()
        if ret != 0:
            log(f"Failed to connect. Error code: {ret} - {company.GetLastErrorDescription()}")
            raise Exception(f"Failed to connect. Error code: {ret} - {company.GetLastErrorDescription()}")

        try:
            for _, row in df.iterrows():
                payment = company.GetBusinessObject(clr.SAPbobsCOM.BoObjectTypes.oIncomingPayments)

                # Set properties
                payment.CardCode = row['customer_id']
                payment.DocType = clr.SAPbobsCOM.BoRcptTypes.rCustomer
                payment.DocDate = DateTime.Parse(row['date'])

                payment.JournalEntries.Lines.AccountCode = row['accounting_code']
                payment.JournalEntries.Lines.Debit = row['price']

                # Set payment lines
                payment.Lines.SetCurrentLine(0)
                payment.Lines.InvoiceType = clr.SAPbobsCOM.BoRcptInvTypes.it_Invoice
                payment.Lines.Total = row['price']
                payment.Lines.Add()

                # Set comments
                payment.Comments = row['comments']

                # Add to SAP B1
                ret = payment.Add()
                if ret != 0:
                    error_msg = f"Failed to add payment for customer {row['customer_id']}. Error: {company.GetLastErrorDescription()}"
                    log(error_msg)
                    raise Exception(error_msg)
                else:
                    success_msg = f"Successfully added payment for customer {row['customer_id']}."
                    log(success_msg)

        finally:
            company.Disconnect()
    '''
    st.code(code, language="python")

page4()