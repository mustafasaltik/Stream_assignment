import unittest
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
from cryptography.fernet import Fernet
import os
from src.main import (decrypt_config_file, read_db_config, load_tsv_file,
                      ingest_data, convert_date_format, remove_duplicates,
                      calculate_total_spending_per_user, add_total_spending_to_users)


class TestMainFunctions(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open, read_data=b'encrypted_config')
    @patch('src.main.Fernet.decrypt', return_value=b'[postgresql]\nuser=postgres\npassword=secret\nhost=localhost\nport=5432\ndatabase=test_db')
    def test_decrypt_config_file(self, mock_fernet_decrypt, mock_open_file):
        # Generate a valid Fernet key
        key = Fernet.generate_key()

        # Call the decrypt_config_file function
        decrypted_data = decrypt_config_file('config.ini.enc', key)

        # Assert that the decrypted content matches the expected output
        self.assertEqual(decrypted_data, '[postgresql]\nuser=postgres\npassword=secret\nhost=localhost\nport=5432\ndatabase=test_db')


    def test_read_db_config(self):
        decrypted_data = '[postgresql]\nuser=postgres\npassword=secret\nhost=localhost\nport=5432\ndatabase=test_db'
        db_config = read_db_config(decrypted_data)
        self.assertEqual(db_config['user'], 'postgres')
        self.assertEqual(db_config['password'], 'secret')
        self.assertEqual(db_config['host'], 'localhost')
        self.assertEqual(db_config['port'], '5432')
        self.assertEqual(db_config['database'], 'test_db')

    @patch('os.path.exists', return_value=True)
    @patch('pandas.read_csv')
    def test_load_tsv_file(self, mock_read_csv, mock_path_exists):
        mock_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        mock_read_csv.return_value = mock_df
        df = load_tsv_file('dummy.csv')
        self.assertIsNotNone(df)
        mock_read_csv.assert_called_once_with('dummy.csv', delimiter='\t')

    @patch('os.path.exists', return_value=False)
    def test_load_tsv_file_not_exists(self, mock_path_exists):
        df = load_tsv_file('dummy.csv')
        self.assertIsNone(df)

    def test_convert_date_format(self):
        transactions_df = pd.DataFrame({
            'Date (UTC)': ['01/01/24 07:00', '02/01/24 07:00'],
            'Total': [100, 200]
        })
        updated_df = convert_date_format(transactions_df)
        self.assertIn('Date (UTC)', updated_df.columns)
        self.assertEqual(pd.to_datetime('2024-01-01 07:00'), updated_df['Date (UTC)'][0])

    def test_remove_duplicates(self):
        df = pd.DataFrame({
            'Customer ID': [1, 2, 2, 3],
            'Total': [100, 200, 200, 300]
        })
        cleaned_df = remove_duplicates(df, 'test_df')
        self.assertEqual(len(cleaned_df), 3)

    def test_calculate_total_spending_per_user(self):
        transactions_df = pd.DataFrame({
            'Customer ID': [1, 2, 2, 3],
            'Total': [100, 200, 200, 300]
        })
        spending_df = calculate_total_spending_per_user(transactions_df)
        self.assertEqual(spending_df.loc[spending_df['Customer ID'] == 1, 'Total Spending'].values[0], 100)
        self.assertEqual(spending_df.loc[spending_df['Customer ID'] == 2, 'Total Spending'].values[0], 400)

    def test_add_total_spending_to_users(self):
        users_df = pd.DataFrame({
            'Customer ID': [1, 2, 3],
            'Customer Name': ['Alice', 'Bob', 'Charlie']
        })
        spending_df = pd.DataFrame({
            'Customer ID': [1, 2],
            'Total Spending': [100, 200]
        })
        updated_df = add_total_spending_to_users(users_df, spending_df)
        self.assertIn('Total Spending', updated_df.columns)
        self.assertEqual(updated_df.loc[updated_df['Customer ID'] == 1, 'Total Spending'].values[0], 100)
        self.assertEqual(updated_df.loc[updated_df['Customer ID'] == 3, 'Total Spending'].values[0], 0)


if __name__ == '__main__':
    unittest.main()
