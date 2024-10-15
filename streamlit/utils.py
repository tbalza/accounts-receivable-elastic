import streamlit as st
import pandas as pd
import sqlite3
from sqlite3 import OperationalError
from datetime import datetime
import time
import inspect
import requests
from elasticsearch import Elasticsearch, helpers
from elasticsearch_dsl import Search, Q
from st_keyup import st_keyup

db_path = 'databases/streamlit.db'

def log(message):
    """Helper function to log messages with a timestamp and the name of the function that called it."""
    # Using inspect to get the name of the caller function
    func_name = inspect.currentframe().f_back.f_code.co_name
    prefix = f"{datetime.now().strftime('%d-%m-%Y - %H:%M')}     {func_name}"
    st.session_state.logs.append(f"{prefix}\t\t{message}")


def load_data_from_sql(table_name):
    """Loads all data from the specified SQL table and logs the process."""
    start_time = time.time()
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    log(f"Connected to database to retrieve entire table: '{table_name}'")
    log(f"Retrieved {len(df)} rows from table: '{table_name}'")
    log(f"Total time to load data: {time.time() - start_time:.2f} seconds.")
    return df

# def load_data_from_sql(table_name):
#     """Loads data from the specified SQL table and logs the process."""
#     start_time = time.time()
#     conn = sqlite3.connect(db_path)
#     log(f"Connecting to database to retrieve table: '{table_name}'")
#     df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
#     conn.close()
#     log(f"Retrieved {len(df)} rows from table: '{table_name}'")
#     log(f"Total time to load data: {time.time() - start_time:.2f} seconds.")
#     log(f"---------------")
#     return df


def found_transactions(from_date, to_date):
    """Fetches remote bank transactions within a date range and compares them to existing ones."""
    start_time = time.time()  # Start timing the process

    formatted_from_date = from_date.strftime('%Y-%m-%d')
    formatted_to_date = to_date.strftime('%Y-%m-%d')

    # FasAPI/dummy-bank endpoint
    api_url = f'http://fastapi:8000/transactions/date_range/?start_date={formatted_from_date}&end_date={formatted_to_date}'

    # Fetch transactions from the API
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        api_transactions = pd.DataFrame(response.json())
        if api_transactions.empty:
            log("No transactions found in specified date range.")
            return api_transactions
        log(f"Connected to remote bank at: {api_url}")
    except requests.RequestException as e:
        log(f"API request error: {e}")
        return pd.DataFrame()

    # Retrieve existing transaction IDs from the database
    try:
        with sqlite3.connect(db_path) as conn:
            current_bank_transactions = pd.read_sql('SELECT id FROM bank', conn)
    except sqlite3.Error as e:
        log(f"Database error: {e}")
        return pd.DataFrame()

    # Filter out current ids
    new_transactions = api_transactions[~api_transactions['id'].isin(current_bank_transactions['id'])]
    if not new_transactions.empty:
        # Add sync date to the new transactions
        new_transactions['bank_sync_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # '%Y-%m-%d %H:%M:%S'
        log(f"Found {len(new_transactions)} new transactions:")
        for _, txn in new_transactions.iterrows():
            log(f"{txn['date']} | {txn['type']} | {txn['sender']} | {txn['description']} | {txn['amount']}")

        log(f"Total time to load data: {time.time() - start_time:.2f} seconds.")
    else:
        log("Bank transactions already synced in specified range.")
    return new_transactions


def sync_transactions(transactions):
    """Writes new transactions to the 'bank' table in the database."""
    if not transactions.empty:
        with sqlite3.connect(db_path) as conn:
            transactions.to_sql('bank', conn, if_exists='append', index=False)
        log(f"{len(transactions)} Transactions successfully synchronized to the automation database.")

def ensure_data(page):
    """Ensure that the necessary data is loaded for each page, loading it if necessary."""
    if 'logs' not in st.session_state:
        st.session_state.logs = []

    if page == 'page1':
        if 'initialized' not in st.session_state:

            # Fetch and sync transactions on initial load
            transactions = found_transactions(st.session_state['start_date'], st.session_state['end_date'])
            sync_transactions(transactions)
            df_bank = load_data_from_sql('bank')

            # Cache the initial fetched and synchronized data
            st.session_state['df_bank'] = df_bank
            st.session_state['initialized'] = True  # Mark as initialized to prevent re-fetching on reloads

    if page in ['page3', 'page4']:
        # Load data from SQL if not already loaded for these pages
        if 'df_bank' not in st.session_state:
            st.session_state.df_bank = load_data_from_sql('bank')
        if 'df_client' not in st.session_state and 'df_student' not in st.session_state:
            st.session_state.df_client = load_data_from_sql('client')
            st.session_state.df_student = load_data_from_sql('student')

    if 'df_client_combined' not in st.session_state and page in ['page3', 'page4', 'page5', 'page6']:
        combine_clients()

    if 'df_bank_terms' not in st.session_state and page == 'page4':
        prepare_bank_terms()

def prepare_bank_terms():
    """Prepares bank search terms for matching by correctly copying df_bank first before adding new column."""
    df_bank_terms = st.session_state.df_bank.copy()  # Correctly copy df_bank to df_bank_terms first.
    df_bank_terms['bank search terms'] = df_bank_terms['sender'].fillna('') + ' ' + df_bank_terms['description'].fillna('')
    st.session_state.df_bank_terms = df_bank_terms
    log("Bank search terms prepared.")


def combine_clients():
    """Combines client and student dataframes and uploads to Elasticsearch."""
    start_time = time.time()
    df_client_combined = pd.merge(st.session_state.df_client, st.session_state.df_student, left_on='client id', right_on='associated client id')
    df_client_combined = df_client_combined.pivot_table(
        index=['client id', 'name', 'last name', 'email1', 'email2', 'handle', 'account number'],
        columns=df_client_combined.groupby("client id").cumcount() + 1,
        values=['student name', 'student last name', 'grade'],
        aggfunc='first'
    ).reset_index()
    df_client_combined.columns = df_client_combined.columns.to_series().apply(
        lambda x: ' '.join(str(y) for y in x if y).strip()
    )
    st.session_state.df_client_combined = df_client_combined
    log(f"Client and student data combined in {time.time() - start_time:.2f} seconds.")
    upload_data_to_elasticsearch(df_client_combined)


def upload_data_to_elasticsearch(df_client_combined):
    """Uploads data to Elasticsearch."""
    start_time = time.time()
    es = Elasticsearch(
        'https://elastic:9200',
        basic_auth=('elastic', 'password'),
        verify_certs=False,
        ssl_show_warn=False
    )
    index_name = "es_client_combined"
    log("Checking if index exists.")
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        log("Index exists. Deleting...")
    es.indices.create(index=index_name)
    log("Creating new index.")
    actions = [
        {
            "_index": index_name,
            "_id": str(record['client id']),
            "_source": record,
        }
        for record in df_client_combined.to_dict(orient='records')
    ]
    helpers.bulk(es, actions)
    es.indices.refresh(index=index_name)
    log(f"Data uploaded to Elasticsearch in {time.time() - start_time:.2f} seconds.")


def get_highest_relevance_clientid(dataframe, index_name, min_score_difference=1.0):
    """Finds the highest relevance client ID for each bank search term."""
    start_time = time.time()
    es = Elasticsearch(
        'https://elastic:9200',
        basic_auth=('elastic', 'password'),
        verify_certs=False,
        ssl_show_warn=False
    )
    def get_clientid(text):
        if not text.strip():
            log(f"Skipped searching due to empty search terms.")
            return None

        query = Q('multi_match', query=text.strip(), fields=['*'], type='best_fields', minimum_should_match="1") # asciifolding, lowercase, ngram, tie_breaker, ^importance
        s = Search(using=es, index=index_name).query(query).extra(size=2)
        response = s.execute()
        log(f"Searching for: {text.strip()}")

        if len(response.hits) > 0:
            top_hit = response.hits[0]
            log(f"Match found: ID {top_hit.meta.id} with score {top_hit.meta.score:.2f}")
            if len(response.hits) == 1:
                return top_hit.meta.id
            elif (top_hit.meta.score - response.hits[1].meta.score >= 1.0):
                return top_hit.meta.id
            else:
                log(f"Ambiguity detected. Close scores between top matches.")
        else:
            log(f"No matches found.")
        return None

    dataframe['matched client id'] = dataframe['bank search terms'].apply(get_clientid).astype('Int64')
    log(f"Elasticsearch queries completed in {time.time() - start_time:.2f} seconds.")
    return dataframe


def search_index():
    """Searches an Elasticsearch index or a DataFrame and displays results in Streamlit, updated dynamically."""
    search_type = st.radio('Select search type:', ['Permissive', 'Elastic ClientID for Bank Transactions'], index=0, horizontal=True, label_visibility="collapsed")
    query = st_keyup('Enter search words:', key="search_query", label_visibility="collapsed", placeholder="Type search terms to start filtering through all combined databases..")  # Dynamic input

    if search_type == 'Permissive':
        if 'df_client_combined' in st.session_state:
            df = st.session_state.df_client_combined
            if query:  # Filter DataFrame based on input
                filter_condition = df.apply(lambda row: query.lower() in str(row).lower(), axis=1)
                filtered_df = df[filter_condition]
                st.dataframe(filtered_df, hide_index=True, width=2000, column_config={"client id": st.column_config.NumberColumn(format="%f")})
            else:  # No input, display the whole DataFrame
                st.dataframe(df, hide_index=True, width=2000, column_config={"client id": st.column_config.NumberColumn(format="%f")})
        else:
            st.error("Data is not available. Please run the combine clients process.")

    else:  # Bank transaction ClientID option
        # Elasticsearch connection
        es = Elasticsearch(
            'https://elastic:9200',
            http_auth=('elastic', 'password'),
            verify_certs=False,
            ssl_show_warn=False
        )
        index_name = 'es_client_combined'

        # Adjust the Elasticsearch query based on user input
        if query:
            search_query = Q('multi_match', query=query, fields=['*'], type='best_fields')  # asciifolding, lowercase, ngram, tie_breaker, ^importance
        else:
            search_query = Q('match_all')

        # Execute search
        search = Search(using=es, index=index_name).query(search_query).extra(size=100)
        response = search.execute()

        # Prepare and display results
        results = []
        for hit in response.hits:
            hit_data = hit.to_dict()
            result = {
                "client id": hit_data.get('client id', ''),
                "name": hit_data.get('name', ''),
                "last name": hit_data.get('last name', ''),
                "email1": hit_data.get('email1', ''),
                "email2": hit_data.get('email2', ''),
                "handle": hit_data.get('handle', ''),
                "account number": hit_data.get('account number', ''),
                "grade 1": hit_data.get('grade 1', ''),
                "grade 2": hit_data.get('grade 2', ''),
                "grade 3": hit_data.get('grade 3', ''),
                "student last name 1": hit_data.get('student last name 1', ''),
                "student name 1": hit_data.get('student name 1', ''),
                "student name 2": hit_data.get('student name 2', ''),
                "student name 3": hit_data.get('student name 3', '')
            }
            results.append(result)

        if results:
            df_results = pd.DataFrame(results)
            st.dataframe(df_results, hide_index=True, width=2000, column_config={"client id": st.column_config.NumberColumn(format="%f")})
        else:
            st.write("No results found.")

