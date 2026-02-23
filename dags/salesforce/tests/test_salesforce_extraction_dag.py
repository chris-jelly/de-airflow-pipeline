"""Tests for the Salesforce extraction DAG (TaskFlow API)."""


class TestSalesforceExtractionDag:
    """Test suite for salesforce_extraction DAG."""

    def test_dag_task_ids(self):
        """Verify DAG contains all expected task IDs."""
        from salesforce_extraction_dag import salesforce_extraction

        dag = salesforce_extraction()
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
        from salesforce_extraction_dag import salesforce_extraction

        dag = salesforce_extraction()

        create_schema = dag.get_task("create_bronze_schema")
        extract_accounts = dag.get_task("extract_accounts")
        extract_opportunities = dag.get_task("extract_opportunities")
        extract_contacts = dag.get_task("extract_contacts")

        # create_bronze_schema should have no upstream dependencies
        assert len(list(create_schema.upstream_list)) == 0

        # All extract tasks should depend on create_bronze_schema
        def upstream_ids(t):
            return {u.task_id for u in t.upstream_list}

        assert "create_bronze_schema" in upstream_ids(extract_accounts)
        assert "create_bronze_schema" in upstream_ids(extract_opportunities)
        assert "create_bronze_schema" in upstream_ids(extract_contacts)

    def test_executor_config_present(self):
        """Verify tasks have executor_config with AIRFLOW_CONN_* env vars."""
        from salesforce_extraction_dag import salesforce_extraction

        dag = salesforce_extraction()

        for task in dag.tasks:
            assert "pod_override" in task.executor_config
            pod = task.executor_config["pod_override"]
            env_names = {e.name for e in pod.spec.containers[0].env}
            assert "AIRFLOW_CONN_WAREHOUSE_POSTGRES" in env_names
            assert "AIRFLOW_CONN_SALESFORCE" in env_names
