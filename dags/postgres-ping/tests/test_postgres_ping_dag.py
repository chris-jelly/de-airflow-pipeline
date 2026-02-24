"""Tests for the Postgres ping DAG."""


class TestPostgresPingDag:
    """Test suite for postgres_ping DAG."""

    def test_dag_parses(self):
        """Verify DAG can be parsed without errors."""
        from postgres_ping_dag import postgres_ping

        dag = postgres_ping()
        assert dag is not None
        assert dag.dag_id == "postgres_ping"

    def test_dag_task_ids(self):
        """Verify DAG contains the expected task ID."""
        from postgres_ping_dag import postgres_ping

        dag = postgres_ping()
        task_ids = {task.task_id for task in dag.tasks}
        assert task_ids == {"ping"}

    def test_dag_schedule(self):
        """Verify DAG schedule is @hourly (cron: 0 * * * *)."""
        from postgres_ping_dag import postgres_ping

        dag = postgres_ping()
        # Airflow 3 normalises @hourly to a CronTriggerTimetable
        assert dag.timetable.summary == "0 * * * *"

    def test_dag_catchup_disabled(self):
        """Verify catchup is False."""
        from postgres_ping_dag import postgres_ping

        dag = postgres_ping()
        assert dag.catchup is False

    def test_executor_config_present(self):
        """Verify ping task has executor_config with AIRFLOW_CONN env var."""
        from postgres_ping_dag import postgres_ping

        dag = postgres_ping()
        ping_task = dag.get_task("ping")
        config = ping_task.executor_config
        assert config is not None, "ping task: executor_config is None"
        assert "pod_override" in config
        pod = config["pod_override"]
        env_names = {e.name for e in pod.spec.containers[0].env}
        assert "AIRFLOW_CONN_WAREHOUSE_POSTGRES" in env_names
