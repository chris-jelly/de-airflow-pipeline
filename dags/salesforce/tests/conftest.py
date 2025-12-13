"""Pytest configuration and fixtures for DAG testing."""

import os
import sys
from unittest.mock import patch

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def mock_airflow_variable():
    """Mock Airflow Variable.get() to avoid needing Airflow DB."""
    with patch("airflow.models.Variable.get") as mock_var:
        mock_var.return_value = "dev"
        yield mock_var
