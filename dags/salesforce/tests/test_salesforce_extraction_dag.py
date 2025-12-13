"""Tests for the Salesforce extraction DAG."""



class TestSalesforceExtractionDag:
    """Test suite for salesforce_extraction DAG."""

    def test_dag_loads(self):
        """Verify DAG can be imported without errors."""
        from salesforce_extraction_dag import dag

        assert dag is not None

    def test_dag_id(self):
        """Verify DAG has the expected ID."""
        from salesforce_extraction_dag import dag

        assert dag.dag_id == "salesforce_extraction"

    def test_dag_has_tasks(self):
        """Verify DAG contains expected tasks."""
        from salesforce_extraction_dag import dag

        assert len(dag.tasks) > 0

    def test_dag_task_ids(self):
        """Verify DAG contains all expected task IDs."""
        from salesforce_extraction_dag import dag

        expected_task_ids = {
            "create_bronze_schema",
            "extract_accounts",
            "extract_opportunities",
            "extract_contacts",
        }
        actual_task_ids = {task.task_id for task in dag.tasks}

        assert expected_task_ids == actual_task_ids

    def test_dag_task_dependencies(self):
        """Verify task dependencies are correctly configured."""
        from salesforce_extraction_dag import dag

        create_schema = dag.get_task("create_bronze_schema")
        extract_accounts = dag.get_task("extract_accounts")
        extract_opportunities = dag.get_task("extract_opportunities")
        extract_contacts = dag.get_task("extract_contacts")

        # create_bronze_schema should have no upstream dependencies
        assert len(create_schema.upstream_list) == 0

        # All extract tasks should depend on create_bronze_schema
        assert create_schema in extract_accounts.upstream_list
        assert create_schema in extract_opportunities.upstream_list
        assert create_schema in extract_contacts.upstream_list

    def test_dag_default_args(self):
        """Verify DAG has expected default args."""
        from salesforce_extraction_dag import dag

        assert dag.default_args["owner"] == "data-team"
        assert dag.default_args["retries"] == 2

    def test_dag_schedule(self):
        """Verify DAG has expected schedule."""
        from salesforce_extraction_dag import dag

        assert str(dag.schedule) == "@daily"
        assert dag.catchup is False
        assert dag.max_active_runs == 1

    def test_executor_config_present(self):
        """Verify tasks have executor_config for Kubernetes."""
        from salesforce_extraction_dag import dag

        for task in dag.tasks:
            assert "pod_override" in task.executor_config
