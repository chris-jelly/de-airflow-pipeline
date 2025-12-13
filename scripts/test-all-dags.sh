#!/bin/bash
set -e

echo "Testing all DAG projects..."

for dag_dir in dags/*/; do
  if [ -f "$dag_dir/pyproject.toml" ]; then
    dag_name=$(basename "$dag_dir")
    echo ""
    echo "========================================"
    echo "Testing $dag_name DAG"
    echo "========================================"

    cd "$dag_dir"
    uv sync
    uv run ruff check .
    uv run pytest -v
    cd - > /dev/null
  fi
done

echo ""
echo "✅ All DAG projects passed!"
