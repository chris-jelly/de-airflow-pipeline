"""
DAG integrity and validation tests.
"""
import os
import sys
from pathlib import Path

import pytest
from airflow.models import DagBag


# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestDAGIntegrity:
    """Test DAG integrity and structure."""

    def setup_method(self):
        """Set up test environment."""
        self.dag_bag = DagBag(dag_folder=str(project_root / "dags"), include_examples=False)

    def test_no_import_errors(self):
        """Test that all DAGs can be imported without errors."""
        assert len(self.dag_bag.import_errors) == 0, f"DAG import errors: {self.dag_bag.import_errors}"

    def test_dag_loaded(self):
        """Test that the main DAG is loaded."""
        assert len(self.dag_bag.dags) > 0, "No DAGs found"
        assert "salesforce_extraction_dag" in self.dag_bag.dags, "salesforce_extraction_dag not found"

    def test_dag_has_tasks(self):
        """Test that DAGs have tasks."""
        for dag_id, dag in self.dag_bag.dags.items():
            assert len(dag.tasks) > 0, f"DAG {dag_id} has no tasks"

    def test_dag_has_tags(self):
        """Test that DAGs have appropriate tags."""
        for dag_id, dag in self.dag_bag.dags.items():
            assert dag.tags is not None, f"DAG {dag_id} has no tags"
            assert len(dag.tags) > 0, f"DAG {dag_id} has empty tags"

    def test_dag_has_owner(self):
        """Test that DAGs have owners specified."""
        for dag_id, dag in self.dag_bag.dags.items():
            assert dag.owner is not None, f"DAG {dag_id} has no owner"
            assert dag.owner != "airflow", f"DAG {dag_id} still has default owner"

    def test_dag_retries_set(self):
        """Test that DAG tasks have appropriate retry settings."""
        for dag_id, dag in self.dag_bag.dags.items():
            for task in dag.tasks:
                # Check that retries are set to a reasonable value
                assert task.retries is not None, f"Task {task.task_id} in DAG {dag_id} has no retry setting"
                assert isinstance(task.retries, int), f"Task {task.task_id} retries should be integer"

    def test_dag_has_description(self):
        """Test that DAGs have descriptions."""
        for dag_id, dag in self.dag_bag.dags.items():
            assert dag.description is not None, f"DAG {dag_id} has no description"
            assert len(dag.description.strip()) > 0, f"DAG {dag_id} has empty description"

    def test_dag_schedule_interval(self):
        """Test that DAGs have reasonable schedule intervals."""
        for dag_id, dag in self.dag_bag.dags.items():
            # Ensure schedule interval is set (can be None for manual trigger)
            assert hasattr(dag, "schedule_interval"), f"DAG {dag_id} has no schedule_interval attribute"

    def test_no_duplicate_task_ids(self):
        """Test that there are no duplicate task IDs within each DAG."""
        for dag_id, dag in self.dag_bag.dags.items():
            task_ids = [task.task_id for task in dag.tasks]
            assert len(task_ids) == len(set(task_ids)), f"DAG {dag_id} has duplicate task IDs"


class TestSalesforceDAGSpecific:
    """Specific tests for the Salesforce extraction DAG."""

    def setup_method(self):
        """Set up test environment."""
        self.dag_bag = DagBag(dag_folder=str(project_root / "dags"), include_examples=False)
        self.dag = self.dag_bag.get_dag("salesforce_extraction_dag")

    def test_salesforce_dag_exists(self):
        """Test that the Salesforce DAG exists."""
        assert self.dag is not None, "salesforce_extraction_dag not found"

    def test_salesforce_dag_structure(self):
        """Test the expected structure of the Salesforce DAG."""
        expected_tasks = [
            "extract_accounts",
            "extract_contacts",
            "extract_opportunities"
        ]

        actual_task_ids = [task.task_id for task in self.dag.tasks]

        for expected_task in expected_tasks:
            assert expected_task in actual_task_ids, f"Expected task {expected_task} not found in DAG"

    def test_salesforce_dag_dependencies(self):
        """Test that DAG tasks have proper dependencies (if any)."""
        # This is a basic check - you might want to add specific dependency tests
        # based on your actual DAG structure
        for task in self.dag.tasks:
            # Ensure tasks have proper upstream/downstream relationships set
            assert hasattr(task, "upstream_task_ids"), f"Task {task.task_id} missing upstream_task_ids"
            assert hasattr(task, "downstream_task_ids"), f"Task {task.task_id} missing downstream_task_ids"