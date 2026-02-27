"""Tests for the Salesforce dbt transformation DAG."""

from datetime import datetime, timezone


def test_should_run_dbt_logic():
    """Verify freshness gate logic for skip vs execute decisions."""
    from salesforce_dbt_transformation_dag import should_run_dbt

    latest = datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc)
    older = datetime(2026, 2, 27, 11, 0, tzinfo=timezone.utc)

    assert not should_run_dbt(None, None)
    assert should_run_dbt(latest, None)
    assert should_run_dbt(latest, older)
    assert not should_run_dbt(older, latest)


class TestSalesforceDbtTransformationDag:
    """DAG structure tests."""

    def test_dag_task_ids(self):
        """Verify DAG contains expected task IDs."""
        from salesforce_dbt_transformation_dag import salesforce_dbt_transformation

        dag = salesforce_dbt_transformation()
        expected = {
            "create_modeling_schemas",
            "check_raw_salesforce_freshness",
            "dbt_build_salesforce",
            "dbt_test_diagnostics",
            "record_last_processed_marker",
        }
        actual = {task.task_id for task in dag.tasks}
        assert actual == expected

    def test_dag_dependencies(self):
        """Verify dependency chain and short-circuit placement."""
        from salesforce_dbt_transformation_dag import salesforce_dbt_transformation

        dag = salesforce_dbt_transformation()

        create_schemas = dag.get_task("create_modeling_schemas")
        freshness_gate = dag.get_task("check_raw_salesforce_freshness")
        dbt_build = dag.get_task("dbt_build_salesforce")
        dbt_diagnostics = dag.get_task("dbt_test_diagnostics")
        record_marker = dag.get_task("record_last_processed_marker")

        assert {task.task_id for task in create_schemas.downstream_list} == {"check_raw_salesforce_freshness"}
        assert {task.task_id for task in freshness_gate.downstream_list} == {"dbt_build_salesforce"}
        assert {task.task_id for task in dbt_build.downstream_list} == {"dbt_test_diagnostics"}
        assert {task.task_id for task in dbt_diagnostics.downstream_list} == {"record_last_processed_marker"}
        assert len(record_marker.downstream_list) == 0

    def test_executor_config_present(self):
        """Verify tasks have executor config with warehouse connection."""
        from salesforce_dbt_transformation_dag import salesforce_dbt_transformation

        dag = salesforce_dbt_transformation()
        for task in dag.tasks:
            config = task.executor_config
            assert config is not None
            assert "pod_override" in config
            pod = config["pod_override"]
            env_names = {env.name for env in pod.spec.containers[0].env}
            assert "AIRFLOW_CONN_WAREHOUSE_POSTGRES" in env_names
