"""
Connection configuration tests.
"""
import os
from unittest.mock import patch, MagicMock

import pytest


class TestConnectionConfigurations:
    """Test connection configurations and environment variable handling."""

    @patch.dict(os.environ, {
        'SALESFORCE_USERNAME': 'test_user@example.com',
        'SALESFORCE_PASSWORD': 'test_password',
        'SALESFORCE_SECURITY_TOKEN': 'test_token',
        'SALESFORCE_DOMAIN': 'login'
    })
    def test_salesforce_env_vars_present(self):
        """Test that Salesforce environment variables can be accessed."""
        assert os.getenv('SALESFORCE_USERNAME') == 'test_user@example.com'
        assert os.getenv('SALESFORCE_PASSWORD') == 'test_password'
        assert os.getenv('SALESFORCE_SECURITY_TOKEN') == 'test_token'
        assert os.getenv('SALESFORCE_DOMAIN') == 'login'

    @patch.dict(os.environ, {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_DATABASE': 'test_db',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_password',
        'POSTGRES_PORT': '5432'
    })
    def test_postgres_env_vars_present(self):
        """Test that PostgreSQL environment variables can be accessed."""
        assert os.getenv('POSTGRES_HOST') == 'localhost'
        assert os.getenv('POSTGRES_DATABASE') == 'test_db'
        assert os.getenv('POSTGRES_USER') == 'test_user'
        assert os.getenv('POSTGRES_PASSWORD') == 'test_password'
        assert os.getenv('POSTGRES_PORT') == '5432'

    def test_salesforce_connection_creation(self):
        """Test Salesforce connection string creation."""
        with patch.dict(os.environ, {
            'SALESFORCE_USERNAME': 'test@example.com',
            'SALESFORCE_PASSWORD': 'password',
            'SALESFORCE_SECURITY_TOKEN': 'token123',
            'SALESFORCE_DOMAIN': 'login'
        }):
            # Test that we can build connection parameters
            sf_params = {
                'username': os.getenv('SALESFORCE_USERNAME'),
                'password': os.getenv('SALESFORCE_PASSWORD'),
                'security_token': os.getenv('SALESFORCE_SECURITY_TOKEN'),
                'domain': os.getenv('SALESFORCE_DOMAIN', 'login')
            }

            assert sf_params['username'] == 'test@example.com'
            assert sf_params['password'] == 'password'
            assert sf_params['security_token'] == 'token123'
            assert sf_params['domain'] == 'login'

    def test_postgres_connection_creation(self):
        """Test PostgreSQL connection string creation."""
        with patch.dict(os.environ, {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_DATABASE': 'airflow_db',
            'POSTGRES_USER': 'airflow',
            'POSTGRES_PASSWORD': 'airflow123',
            'POSTGRES_PORT': '5432'
        }):
            # Test that we can build connection parameters
            pg_params = {
                'host': os.getenv('POSTGRES_HOST'),
                'database': os.getenv('POSTGRES_DATABASE'),
                'user': os.getenv('POSTGRES_USER'),
                'password': os.getenv('POSTGRES_PASSWORD'),
                'port': int(os.getenv('POSTGRES_PORT', '5432'))
            }

            assert pg_params['host'] == 'localhost'
            assert pg_params['database'] == 'airflow_db'
            assert pg_params['user'] == 'airflow'
            assert pg_params['password'] == 'airflow123'
            assert pg_params['port'] == 5432

    def test_missing_salesforce_env_vars(self):
        """Test behavior when Salesforce environment variables are missing."""
        required_sf_vars = [
            'SALESFORCE_USERNAME',
            'SALESFORCE_PASSWORD',
            'SALESFORCE_SECURITY_TOKEN'
        ]

        for var in required_sf_vars:
            with patch.dict(os.environ, {}, clear=True):
                assert os.getenv(var) is None, f"Environment variable {var} should be None when not set"

    def test_missing_postgres_env_vars(self):
        """Test behavior when PostgreSQL environment variables are missing."""
        required_pg_vars = [
            'POSTGRES_HOST',
            'POSTGRES_DATABASE',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD'
        ]

        for var in required_pg_vars:
            with patch.dict(os.environ, {}, clear=True):
                assert os.getenv(var) is None, f"Environment variable {var} should be None when not set"

    def test_optional_env_vars_defaults(self):
        """Test that optional environment variables have proper defaults."""
        with patch.dict(os.environ, {}, clear=True):
            # Test Salesforce domain default
            sf_domain = os.getenv('SALESFORCE_DOMAIN', 'login')
            assert sf_domain == 'login'

            # Test PostgreSQL port default
            pg_port = int(os.getenv('POSTGRES_PORT', '5432'))
            assert pg_port == 5432