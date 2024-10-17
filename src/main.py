import pandas as pd
import os
import logging
import configparser
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy import text
import streamlit as st

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def decrypt_config_file(encrypted_file, key):
    """
    Decrypt the encrypted config file using the provided key.

    Parameters:
    - encrypted_file: str, path to the encrypted config file.
    - key: bytes, the encryption key.

    Returns:
    - decrypted_data: str, decrypted content of the config file.
    """
    f = Fernet(key)

    # Read the encrypted config file
    with open(encrypted_file, "rb") as file:
        encrypted_data = file.read()

    # Decrypt the data
    decrypted_data = f.decrypt(encrypted_data)

    # Return the decrypted data as a string
    return decrypted_data.decode()


def read_db_config(decrypted_data):
    """
    Parse the decrypted config data using configparser.

    Parameters:
    - decrypted_data: str, decrypted config data.

    Returns:
    - db_config: dict, database connection information.
    """
    config = configparser.ConfigParser()

    # Read the decrypted data into configparser
    config.read_string(decrypted_data)

    db_config = {
        'user': config['postgresql']['user'],
        'password': config['postgresql']['password'],
        'host': config['postgresql']['host'],
        'port': config['postgresql']['port'],
        'database': config['postgresql']['database']
    }

    return db_config


def load_tsv_file(file_path, delimiter='\t'):
    """
    Load a CSV/TSV file into a pandas DataFrame.

    Parameters:
    - file_path: str, the path to the CSV/TSV file.
    - delimiter: str, the delimiter used in the file (default is '\t' for TSV).

    Returns:
    - df: pandas DataFrame, the loaded data.
    """
    if not os.path.exists(file_path):
        logging.error(f"The file {file_path} does not exist.")
        return None

    try:
        df = pd.read_csv(file_path, delimiter=delimiter)
        logging.info(f"Loaded {len(df)} records from {file_path}")
        return df
    except Exception as e:
        logging.error(f"Error loading {file_path}: {e}")
        return None


def ingest_data(products_file, transactions_file, users_file):
    """
    Ingests data from three files: products, transactions, and users.

    Parameters:
    - products_file: str, the path to the products file.
    - transactions_file: str, the path to the transactions file.
    - users_file: str, the path to the users file.

    Returns:
    - products_df: pandas DataFrame, the products data.
    - transactions_df: pandas DataFrame, the transactions data.
    - users_df: pandas DataFrame, the users data.
    """
    # Load each file into a DataFrame
    products_df = load_tsv_file(products_file)
    transactions_df = load_tsv_file(transactions_file)
    users_df = load_tsv_file(users_file)

    # Convert the date format in the transactions data
    if transactions_df is not None:
        transactions_df = convert_date_format(transactions_df)

    # Remove duplicates from each DataFrame
    if products_df is not None:
        products_df = remove_duplicates(products_df, 'products_df')
    if transactions_df is not None:
        transactions_df = remove_duplicates(transactions_df, 'transactions_df')
    if users_df is not None:
        users_df = remove_duplicates(users_df, 'users_df').groupby('Customer ID').agg({
            'Customer Name': 'last',  # Keeping the last customer name to have same names in everywhere
            'Customer Email': 'last',  # Keeping the last customer email to have same email address in everywhere
        }).reset_index()

    return products_df, transactions_df, users_df


def convert_date_format(transactions_df):
    """
    Convert the date format in the transactions DataFrame.

    Parameters:
    - transactions_df: pandas DataFrame, the transactions data.

    Returns:
    - transactions_df: pandas DataFrame, the updated transactions data with formatted dates.
    """
    # Check if the 'Date (UTC)' column exists
    if 'Date (UTC)' in transactions_df.columns:
        # Convert the 'Date (UTC)' column to the desired format
        transactions_df['Date (UTC)'] = pd.to_datetime(transactions_df['Date (UTC)'], format='%m/%d/%y %H:%M')
        logging.info("Date format converted to 'YYYY-MM-DD HH:MI:00'")
    else:
        logging.warning("Date (UTC) column not found in transactions data.")

    return transactions_df


def log_example_rows(df, df_name, num_rows=5):
    """
    Logs the first few rows of a DataFrame using logging.

    Parameters:
    - df: pandas DataFrame, the DataFrame to log.
    - df_name: str, name of the DataFrame for logging.
    - num_rows: int, number of rows to display (default is 5).
    """
    if df is not None:
        logging.info(f"Example rows from {df_name}:")
        logging.info("\n" + df.head(num_rows).to_string())
    else:
        logging.warning(f"{df_name} is empty or not loaded.")


def remove_duplicates(df, df_name):
    """
    Remove duplicate records from a DataFrame.

    Parameters:
    - df: pandas DataFrame, the DataFrame to remove duplicates from.
    - df_name: str, name of the DataFrame for logging.

    Returns:
    - df: pandas DataFrame, the DataFrame with duplicates removed.
    """
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    logging.info(f"Removed {before - after} duplicate rows from {df_name}. Remaining rows: {after}")
    return df


def calculate_total_spending_per_user(transactions_df):
    """
    Calculate total spending per user by grouping by Customer ID.

    Parameters:
    - transactions_df: pandas DataFrame, the transactions data.

    Returns:
    - spending_per_user_df: pandas DataFrame, total spending per user.
    """
    # Group by 'Customer ID' and calculate total spending
    spending_per_user_df = transactions_df.groupby('Customer ID', as_index=False)['Total'].sum()
    spending_per_user_df.rename(columns={'Total': 'Total Spending'}, inplace=True)

    return spending_per_user_df


def add_total_spending_to_users(users_df, spending_per_user_df):
    """
    Add the 'Total Spending' column to the users DataFrame by merging with spending_per_user_df.

    Parameters:
    - users_df: pandas DataFrame, the users data.
    - spending_per_user_df: pandas DataFrame, total spending per user.

    Returns:
    - updated_users_df: pandas DataFrame, the users data with total spending column.
    """
    # Merge total spending with users_df
    updated_users_df = pd.merge(users_df, spending_per_user_df, on='Customer ID', how='left')

    # Fill NaN values in 'Total Spending' with 0 (in case some users have no transactions)
    updated_users_df['Total Spending'] = updated_users_df['Total Spending'].fillna(0)

    return updated_users_df


def get_db_config():
    # Load and decrypt the config file
    key = open("src/secret.key", "rb").read()
    decrypted_config = decrypt_config_file("src/config.ini.enc", key)

    # Parse the database configuration
    return read_db_config(decrypted_config)


def standardize_column_names(df):
    """
    Standardize column names by removing spaces and converting to lowercase.

    Parameters:
    - df: pandas DataFrame, the DataFrame whose columns need to be standardized.

    Returns:
    - df: pandas DataFrame, the DataFrame with standardized column names.
    """
    df.columns = df.columns.str.replace(' ', '_')\
        .str.replace('(', '')\
        .str.replace(')', '')\
        .str.lower()
    return df


def save_to_postgres(engine, df, table_name, primary_key=None):
    """
    Save a pandas DataFrame to a PostgreSQL database after standardizing column names
    and optionally add a primary key constraint.

    Parameters:
    - engine: SQLAlchemy engine connected to PostgreSQL.
    - df: pandas DataFrame, the data to save.
    - table_name: str, the name of the table to save the data.
    - primary_key: str, the column name to use as the primary key (optional).
    """
    # Standardize the column names
    df = standardize_column_names(df)

    df.to_sql(table_name, engine, if_exists='replace', index=False)
    logging.info(f"Data saved to table '{table_name}'")

    # Add primary key constraint if provided
    if primary_key:
        if isinstance(primary_key, list):
            pk_columns = ', '.join(primary_key)  # Join the columns with commas for composite PK
        else:
            pk_columns = primary_key  # Single column primary key

        with engine.connect() as conn:
            alter_query = f'ALTER TABLE {table_name} ADD PRIMARY KEY ({pk_columns});'
            conn.execute(text(alter_query))
            conn.commit()
            logging.info(f"Primary key '{pk_columns}' added to table '{table_name}'.\n"
                         f"Alter_query: '{alter_query}'")


def get_postgres_engine():
    db_config = get_db_config()

    # Create the PostgreSQL engine
    engine = create_engine(
        f'postgresql://{db_config["user"]}:{db_config["password"]}@{db_config["host"]}:{db_config["port"]}/{db_config["database"]}')

    logging.info(f"Successfully connected to PostgreSQL database {db_config['database']} at {db_config['host']}")

    return engine


# Query data from PostgreSQL
@st.cache_resource
def query_data(query):
    engine = get_postgres_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=query,
            con=conn.connection
        )
    return df


if __name__ == '__main__':
    products_file = "input/products.csv"
    transactions_file = "input/transactions.csv"
    users_file = "input/users.csv"

    products_df, transactions_df, users_df = ingest_data(products_file, transactions_file, users_file)

    # Calculate total spending per user
    spending_per_user_df = calculate_total_spending_per_user(transactions_df)

    # Add total spending as a new column in the users DataFrame
    updated_users_df = add_total_spending_to_users(users_df, spending_per_user_df)

    # Log example rows from final users_df
    log_example_rows(updated_users_df, 'users_df')

    # Open postgres connection and get the engine
    engine = get_postgres_engine()

    # Save the DataFrames to the PostgreSQL database
    save_to_postgres(engine, products_df, 'dim_product', primary_key=['subscription_id', 'plan'])
    save_to_postgres(engine, transactions_df, 'fct_transaction', primary_key='transaction_id')
    save_to_postgres(engine, updated_users_df, 'dim_user', primary_key='customer_id')