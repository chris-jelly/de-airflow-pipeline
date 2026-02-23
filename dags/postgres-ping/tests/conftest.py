"""Pytest configuration and fixtures for postgres-ping DAG testing."""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
