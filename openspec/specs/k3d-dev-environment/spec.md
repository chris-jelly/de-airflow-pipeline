## ADDED Requirements

### Requirement: Airflow 3 image in Helm values

The K3d Helm values SHALL specify `apache/airflow:3.1.5-python3.13` as the base Airflow image, matching the version used in DAG Dockerfiles and `pyproject.toml` dependencies.

#### Scenario: Image tag updated

- **WHEN** `k3d/values-airflow.yaml` is inspected
- **THEN** `images.airflow.tag` SHALL be `3.1.5-python3.13`

#### Scenario: Scheduler and webserver run Airflow 3

- **WHEN** the K3d cluster is deployed with these Helm values
- **THEN** the scheduler, webserver, and triggerer pods SHALL run the `apache/airflow:3.1.5-python3.13` image

### Requirement: KubernetesExecutor config section renamed

The Airflow configuration in Helm values SHALL use the `kubernetes_executor` section key instead of the deprecated `kubernetes` key.

#### Scenario: Config section name

- **WHEN** `k3d/values-airflow.yaml` is inspected
- **THEN** the config section SHALL be `config.kubernetes_executor` with key `delete_worker_pods: 'True'`
- **THEN** there SHALL be no `config.kubernetes` section

### Requirement: Legacy API auth config removed

The Helm values SHALL NOT include `config.api.auth_backends` since Airflow 3 replaced the Flask-based REST API with a FastAPI-based API that uses its own authentication mechanism.

#### Scenario: No API auth backends config

- **WHEN** `k3d/values-airflow.yaml` is inspected
- **THEN** the `config.api` section SHALL NOT contain an `auth_backends` key

### Requirement: Documentation updated to Airflow 3

`CONTAINER_STRATEGY.md` and `KUBERNETES.md` SHALL be updated to reference Airflow 3.x image tags and patterns. All references to `apache/airflow:2.8.1` or `2.8.1-python3.11` SHALL be replaced with the current `3.1.5-python3.13` version.

#### Scenario: CONTAINER_STRATEGY.md references current version

- **WHEN** `CONTAINER_STRATEGY.md` is inspected
- **THEN** all Airflow image references SHALL use `3.1.5-python3.13` and there SHALL be no references to `2.8.1`

#### Scenario: KUBERNETES.md references current version

- **WHEN** `KUBERNETES.md` is inspected
- **THEN** all Airflow image references SHALL use `3.1.5-python3.13` and there SHALL be no references to `2.8.1`

### Requirement: Celery components remain disabled

The Helm values SHALL continue to explicitly disable `flower` and `redis` since the cluster uses KubernetesExecutor.

#### Scenario: Flower and Redis disabled

- **WHEN** `k3d/values-airflow.yaml` is inspected
- **THEN** `flower.enabled` SHALL be `false` and `redis.enabled` SHALL be `false`

### Requirement: K3d AGENTS.md updated

The `k3d/AGENTS.md` file SHALL be updated to reflect Airflow 3 configuration patterns, including the renamed config section and removal of legacy API auth guidance.

#### Scenario: AGENTS.md reflects Airflow 3

- **WHEN** `k3d/AGENTS.md` is inspected
- **THEN** references to `config.kubernetes` SHALL be updated to `config.kubernetes_executor`
- **THEN** API authentication guidance SHALL reflect the Airflow 3 FastAPI-based API
