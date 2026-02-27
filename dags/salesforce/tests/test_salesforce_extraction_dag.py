"""Tests for the Salesforce extraction DAG (TaskFlow API)."""

from datetime import datetime, timezone


def test_curated_fields_include_id_and_systemmodstamp():
    """Verify each object field list includes required incremental keys."""
    from salesforce_extraction_dag import CURATED_FIELDS

    for sf_object, fields in CURATED_FIELDS.items():
        assert "Id" in fields, f"{sf_object} missing Id"
        assert "SystemModstamp" in fields, f"{sf_object} missing SystemModstamp"


def test_query_uses_explicit_fields_not_wildcard():
    """Verify SOQL uses explicit curated fields and not SELECT *."""
    from salesforce_extraction_dag import CURATED_FIELDS, build_incremental_query

    for sf_object, fields in CURATED_FIELDS.items():
        query = build_incremental_query(sf_object, watermark=None)
        assert "SELECT *" not in query
        assert query.startswith(f"SELECT {', '.join(fields)} FROM {sf_object}")


def test_query_uses_schema_compatible_selected_fields():
    """Verify query can be built from schema-compatible selected fields."""
    from salesforce_extraction_dag import build_incremental_query_with_fields

    selected_fields = ["Id", "AccountId", "Name", "SystemModstamp"]
    query = build_incremental_query_with_fields(
        sf_object="Opportunity",
        selected_fields=selected_fields,
        watermark=None,
    )

    assert "SELECT *" not in query
    assert query.startswith(
        "SELECT Id, AccountId, Name, SystemModstamp FROM Opportunity"
    )


def test_select_schema_compatible_fields_skips_missing_optional_fields():
    """Verify optional curated fields are skipped when unavailable in org schema."""
    from salesforce_extraction_dag import select_schema_compatible_fields

    available_fields = {
        "Id",
        "AccountId",
        "Name",
        "StageName",
        "Amount",
        "SystemModstamp",
    }

    selected, skipped = select_schema_compatible_fields(
        sf_object="Opportunity",
        available_fields=available_fields,
    )

    assert "CurrencyIsoCode" in skipped
    assert "CurrencyIsoCode" not in selected
    assert "Id" in selected
    assert "SystemModstamp" in selected


def test_select_schema_compatible_fields_fails_when_required_field_missing():
    """Verify required tracking fields are validated after compatibility filtering."""
    import pytest

    from salesforce_extraction_dag import select_schema_compatible_fields

    available_fields = {"Id", "Name"}

    with pytest.raises(ValueError, match="missing required fields"):
        select_schema_compatible_fields(
            sf_object="Opportunity",
            available_fields=available_fields,
        )


def test_query_applies_watermark_and_deterministic_ordering():
    """Verify incremental query contains watermark filter and deterministic ordering."""
    from salesforce_extraction_dag import build_incremental_query

    watermark = datetime(2026, 2, 26, 12, 0, tzinfo=timezone.utc)
    query = build_incremental_query("Account", watermark=watermark)

    assert "WHERE SystemModstamp >" in query
    assert query.endswith("ORDER BY SystemModstamp, Id")


def test_next_watermark_bootstrap_and_advancement_rules():
    """Verify watermark behavior for bootstrap, no-op, and advance cases."""
    from salesforce_extraction_dag import next_watermark

    now = datetime(2026, 2, 26, 13, 0, tzinfo=timezone.utc)
    existing = datetime(2026, 2, 25, 13, 0, tzinfo=timezone.utc)

    bootstrap_value = next_watermark(current=None, records=[], now_utc=now)
    assert bootstrap_value == now

    unchanged_value = next_watermark(current=existing, records=[], now_utc=now)
    assert unchanged_value == existing

    advanced_value = next_watermark(
        current=existing,
        records=[
            {"SystemModstamp": "2026-02-26T13:10:00.000+0000"},
            {"SystemModstamp": "2026-02-26T13:20:00.000+0000"},
        ],
        now_utc=now,
    )
    assert advanced_value == datetime(2026, 2, 26, 13, 20, tzinfo=timezone.utc)


def test_delete_strategy_remains_out_of_scope():
    """Verify DAG module does not implement Salesforce delete-replication APIs."""
    import inspect

    import salesforce_extraction_dag

    source = inspect.getsource(salesforce_extraction_dag)
    assert "getDeleted" not in source
    assert "getUpdated" not in source


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
            config = task.executor_config
            assert config is not None, f"Task {task.task_id}: executor_config is None"
            assert "pod_override" in config
            pod = config["pod_override"]
            env_names = {e.name for e in pod.spec.containers[0].env}
            assert "AIRFLOW_CONN_WAREHOUSE_POSTGRES" in env_names
            assert "AIRFLOW_CONN_SALESFORCE" in env_names

    def test_image_pull_policy_always(self):
        """Verify executor pods use imagePullPolicy=Always to pick up new images."""
        from salesforce_extraction_dag import salesforce_extraction

        dag = salesforce_extraction()

        for task in dag.tasks:
            config = task.executor_config
            assert config is not None, f"Task {task.task_id}: executor_config is None"
            pod = config["pod_override"]
            container = pod.spec.containers[0]
            assert container.image_pull_policy == "Always", (
                f"Task {task.task_id}: expected imagePullPolicy=Always, "
                f"got {container.image_pull_policy}"
            )
