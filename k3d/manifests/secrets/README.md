# Kubernetes Secrets for Local Development

This directory contains templates for Kubernetes secrets. **DO NOT commit actual secret files to git.**

## Creating Secrets

### Option 1: Use the automated script (Recommended)

```bash
cd k3d/scripts
./secrets-setup.sh
```

This interactive script will prompt you for all credentials and create the secrets in your cluster.

### Option 2: Manual creation

1. Copy the template files and remove the `.template` extension:

```bash
cp salesforce-credentials.yaml.template salesforce-credentials.yaml
cp postgres-credentials.yaml.template postgres-credentials.yaml
```

2. Edit each file and replace the placeholder values with base64-encoded credentials:

```bash
# Encode your values
echo -n "your-consumer-key" | base64
echo -n "your-consumer-secret" | base64
echo -n "postgres-target.airflow.svc.cluster.local" | base64
echo -n "warehouse" | base64
echo -n "airflow" | base64
echo -n "airflow123" | base64
```

3. Apply the secrets to your cluster:

```bash
kubectl apply -f salesforce-credentials.yaml
kubectl apply -f postgres-credentials.yaml
```

## Required Secrets

### salesforce-credentials

Required for Salesforce OAuth authentication:
- `consumer_key`: OAuth Consumer Key from your Salesforce Connected App
- `consumer_secret`: OAuth Consumer Secret from your Salesforce Connected App

### postgres-credentials

Required for PostgreSQL target database connection:
- `host`: PostgreSQL hostname (use `postgres-target.airflow.svc.cluster.local` for local k3d)
- `database`: Database name (e.g., `warehouse`)
- `username`: Database username (e.g., `airflow`)
- `password`: Database password

## Security Notes

- The `*.yaml` files (without `.template`) are gitignored
- Never commit actual credentials
- Use strong passwords for PostgreSQL
- Rotate credentials regularly in production environments
