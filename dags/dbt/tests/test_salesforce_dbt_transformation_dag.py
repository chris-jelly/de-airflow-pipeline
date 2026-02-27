"""Tests for the Salesforce dbt transformation DAG."""

from datetime import datetime, timezone
import logging
import subprocess
import sys
import types

import pytest


def test_should_run_dbt_logic():
    """Verify freshness gate logic for skip vs execute decisions."""
    from salesforce_dbt_transformation_dag import should_run_dbt

    latest = datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc)
    older = datetime(2026, 2, 27, 11, 0, tzinfo=timezone.utc)

    assert not should_run_dbt(None, None)
    assert should_run_dbt(latest, None)
    assert should_run_dbt(latest, older)
    assert not should_run_dbt(older, latest)


def _install_fake_postgres_hook(monkeypatch):
    class DummyConnection:
        host = "warehouse.local"
        login = "airflow"
        password = "secret"
        port = 5432
        schema = "warehouse"

    class DummyPostgresHook:
        def __init__(self, postgres_conn_id):
            self.postgres_conn_id = postgres_conn_id

        def get_connection(self, conn_id):
            assert conn_id == "warehouse_postgres"
            return DummyConnection()

    module = types.ModuleType("airflow.providers.postgres.hooks.postgres")
    module.PostgresHook = DummyPostgresHook
    monkeypatch.setitem(sys.modules, "airflow.providers.postgres.hooks.postgres", module)


def test_build_dbt_env_includes_writable_runtime_paths(monkeypatch):
    """Verify dbt env routes runtime artifacts to writable /tmp paths."""
    _install_fake_postgres_hook(monkeypatch)

    from salesforce_dbt_transformation_dag import _build_dbt_env

    env = _build_dbt_env()

    assert env["DBT_TARGET_PATH"] == "/tmp/dbt/target"
    assert env["DBT_LOG_PATH"] == "/tmp/dbt/logs"
    assert env["DBT_PACKAGES_INSTALL_PATH"] == "/tmp/dbt/dbt_packages"


def test_run_dbt_command_logs_output_on_failure(monkeypatch, caplog):
    """Verify dbt failure path logs command, stdout, and stderr."""
    _install_fake_postgres_hook(monkeypatch)

    from salesforce_dbt_transformation_dag import _run_dbt_command

    def _raise_failure(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=2,
            cmd=args[0],
            output="compile output",
            stderr="syntax error",
        )

    monkeypatch.setattr(subprocess, "run", _raise_failure)

    caplog.set_level(logging.INFO)
    with pytest.raises(subprocess.CalledProcessError):
        _run_dbt_command(["dbt", "build"])

    logs = "\n".join(caplog.messages)
    assert "dbt command failed with exit code 2" in logs
    assert "dbt stdout:" in logs
    assert "compile output" in logs
    assert "dbt stderr:" in logs
    assert "syntax error" in logs


def test_run_dbt_command_uses_shared_runtime_env(monkeypatch):
    """Verify dbt command execution receives shared writable env paths."""
    _install_fake_postgres_hook(monkeypatch)

    from salesforce_dbt_transformation_dag import _run_dbt_command

    captured = {}

    def _capture_run(*args, **kwargs):
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", _capture_run)

    _run_dbt_command(["dbt", "test", "--select", "tag:warn"])

    env = captured["kwargs"]["env"]
    assert env["DBT_TARGET_PATH"] == "/tmp/dbt/target"
    assert env["DBT_LOG_PATH"] == "/tmp/dbt/logs"
    assert env["DBT_PACKAGES_INSTALL_PATH"] == "/tmp/dbt/dbt_packages"


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
