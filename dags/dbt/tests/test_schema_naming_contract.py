"""Tests for dbt schema naming contract."""

from pathlib import Path


def test_generate_schema_macro_disables_prefix_concat():
    """Ensure custom dbt schema names are not prefixed by target schema."""
    macro_path = Path(__file__).resolve().parent.parent / "macros" / "generate_schema_name.sql"
    macro_sql = macro_path.read_text()

    assert "macro generate_schema_name(custom_schema_name, node)" in macro_sql
    assert "{{ custom_schema_name | trim }}" in macro_sql
    assert "default_schema" not in macro_sql
    assert "_{{ custom_schema_name" not in macro_sql


def test_profile_notes_canonical_modeled_schemas():
    """Ensure profile documents canonical schema contract for Salesforce models."""
    profile_path = Path(__file__).resolve().parent.parent / "profiles.yml"
    profile_yaml = profile_path.read_text()

    assert "schemas: staging, intermediate, marts" in profile_yaml
