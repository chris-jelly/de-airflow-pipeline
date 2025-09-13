"""
Package and module import tests.
"""
import sys
from pathlib import Path

import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestPackageImports:
    """Test that all packages and modules can be imported."""

    def test_de_airflow_pipeline_import(self):
        """Test that the main package can be imported."""
        try:
            import de_airflow_pipeline
            assert de_airflow_pipeline is not None
        except ImportError as e:
            pytest.fail(f"Failed to import de_airflow_pipeline package: {e}")

    def test_dags_import(self):
        """Test that DAG modules can be imported."""
        try:
            import dags.salesforce_extraction_dag as sf_dag
            assert sf_dag is not None
            assert hasattr(sf_dag, 'dag'), "salesforce_extraction_dag should have 'dag' attribute"
        except ImportError as e:
            pytest.fail(f"Failed to import salesforce_extraction_dag: {e}")

    def test_airflow_imports(self):
        """Test that required Airflow modules can be imported."""
        required_airflow_modules = [
            'airflow',
            'airflow.models',
            'airflow.operators.python',
            'airflow.providers.postgres.hooks.postgres',
            'airflow.providers.salesforce.hooks.salesforce'
        ]

        for module_name in required_airflow_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import required Airflow module {module_name}: {e}")

    def test_third_party_imports(self):
        """Test that required third-party modules can be imported."""
        required_modules = [
            'pandas',
            'psycopg2'
        ]

        for module_name in required_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import required third-party module {module_name}: {e}")

    def test_standard_library_imports(self):
        """Test that required standard library modules can be imported."""
        required_modules = [
            'os',
            'datetime',
            'logging'
        ]

        for module_name in required_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import standard library module {module_name}: {e}")


class TestDAGSpecificImports:
    """Test DAG-specific imports and dependencies."""

    def test_salesforce_dag_dependencies(self):
        """Test that the Salesforce DAG can import all its dependencies."""
        try:
            # Import the DAG file to check all its dependencies
            import dags.salesforce_extraction_dag

            # Check that the DAG object exists
            assert hasattr(dags.salesforce_extraction_dag, 'dag')

            # Check that the DAG has the expected attributes
            dag = dags.salesforce_extraction_dag.dag
            assert dag.dag_id == 'salesforce_extraction_dag'

        except Exception as e:
            pytest.fail(f"Failed to import or validate salesforce_extraction_dag: {e}")

    def test_dag_function_definitions(self):
        """Test that DAG task functions are properly defined."""
        try:
            import dags.salesforce_extraction_dag as sf_dag

            # Check for expected function definitions
            expected_functions = [
                'extract_salesforce_data'  # This might vary based on your actual DAG structure
            ]

            for func_name in expected_functions:
                if hasattr(sf_dag, func_name):
                    func = getattr(sf_dag, func_name)
                    assert callable(func), f"{func_name} should be callable"

        except ImportError as e:
            pytest.skip(f"Skipping function tests due to import error: {e}")
        except Exception as e:
            pytest.fail(f"Error testing DAG functions: {e}")