# ADR-003: External Secrets Operator for Azure Key Vault

**Status**: Accepted

**Date**: 2025-11-26

**Deciders**: Platform Team

## Context

Secrets need to be synchronized from Azure Key Vault (our source of truth) into Kubernetes Secrets that can be consumed by Airflow executor pods.

Options for syncing secrets from Azure to Kubernetes:
1. Manual creation of Kubernetes Secrets
2. External Secrets Operator (ESO)
3. Azure Key Vault Provider for Secrets Store CSI Driver
4. Custom sync scripts/controllers

Key requirements:
- Azure Key Vault as source of truth
- Automatic synchronization and updates
- Support for multiple namespaces
- Minimal operational overhead
- Standard Kubernetes Secret resources as output

## Decision

We will use **External Secrets Operator (ESO)** to automatically sync secrets from Azure Key Vault into Kubernetes as standard `Secret` resources.

**Implementation:**
- ESO watches `ExternalSecret` CRDs
- ESO connects to Azure Key Vault using a `SecretStore` or `ClusterSecretStore`
- ESO creates/updates standard Kubernetes `Secret` resources
- Airflow DAGs reference these secrets in their `executor_config`

## Consequences

### Positive
- **Automatic sync**: Secrets updated in Azure automatically sync to Kubernetes
- **GitOps friendly**: `ExternalSecret` manifests can be version controlled
- **Standard output**: Creates normal Kubernetes Secrets that work with existing tools
- **Multi-cloud support**: Can add other secret sources later (Vault, AWS, GCP)
- **Namespace scoped**: Different namespaces can access different secrets
- **Active community**: Well-maintained, widely adopted project
- **Flexible templating**: Can transform secret structure during sync

### Negative
- **Another operator**: Adds operational dependency (ESO must be healthy)
- **Secrets in etcd**: Secrets are stored in Kubernetes etcd (mitigated by encryption at rest)
- **Sync delay**: Small delay between Azure update and K8s availability
- **CRD complexity**: Requires understanding of ESO CRD structure

### Neutral
- **Azure authentication**: Requires workload identity or service principal setup
- **Monitoring needed**: Need to monitor ESO sync status

## Alternatives Considered

### Alternative 1: Manual Secret Creation

**Description**: Manually create Kubernetes Secrets using `kubectl create secret`

```bash
kubectl create secret generic salesforce-credentials \
  --from-literal=username='...' \
  --namespace=airflow
```

**Pros**:
- Simple, no additional tools
- Direct control over secrets

**Cons**:
- Not automated (secrets don't update automatically)
- Not GitOps friendly (secrets not in version control)
- Error prone (manual typos, forgotten updates)
- No audit trail
- Difficult to rotate across multiple environments

**Why not chosen**: Not suitable for production. Manual processes don't scale and are error-prone. No way to ensure Azure Key Vault and K8s are in sync.

### Alternative 2: Azure Key Vault CSI Driver

**Description**: Mount secrets directly from Azure Key Vault into pods using CSI driver

```yaml
volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      volumeAttributes:
        secretProviderClass: "azure-secrets"
```

**Pros**:
- Secrets never stored in Kubernetes etcd
- Direct mount from Azure (no intermediate storage)
- Can sync to environment variables or files

**Cons**:
- More complex pod configuration
- CSI driver must be installed and healthy
- Secrets mounted as files, not K8s Secret resources
- Harder to use with applications expecting K8s secrets
- More complex troubleshooting

**Why not chosen**: While more secure (secrets not in etcd), it adds significant complexity. Our current setup with encrypted etcd meets security requirements. ESO with standard Secrets is easier to work with and more flexible.

### Alternative 3: Custom Sync Script/Controller

**Description**: Write custom code to sync from Azure Key Vault to Kubernetes

**Pros**:
- Full control over sync logic
- Can customize to exact needs

**Cons**:
- Maintenance burden (we own the code)
- Need to handle auth, retries, errors, rate limiting
- Need to deploy and monitor custom controller
- Reinventing the wheel

**Why not chosen**: ESO already solves this problem well. Building and maintaining custom sync logic is not a good use of engineering time.

### Alternative 4: Sealed Secrets

**Description**: Encrypt secrets in Git, decrypt in cluster

**Pros**:
- Secrets in version control
- GitOps native

**Cons**:
- Doesn't sync from Azure Key Vault (our source of truth)
- Need to manually update sealed secrets when Azure changes
- Another encryption layer to manage
- Secrets still need to originate somewhere

**Why not chosen**: Doesn't solve our core problem of syncing from Azure Key Vault. We want Azure as the single source of truth, not Git.

## Implementation Notes

**Example SecretStore configuration (managed by platform team):**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: azure-key-vault
  namespace: airflow
spec:
  provider:
    azurekv:
      authType: WorkloadIdentity
      vaultUrl: "https://my-vault.vault.azure.net"
      serviceAccountRef:
        name: external-secrets-sa
```

**Example ExternalSecret for Salesforce credentials:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: salesforce-credentials
  namespace: airflow
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: azure-key-vault
    kind: SecretStore
  target:
    name: salesforce-credentials
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: salesforce-username
    - secretKey: password
      remoteRef:
        key: salesforce-password
    - secretKey: security_token
      remoteRef:
        key: salesforce-security-token
```

This creates a standard Kubernetes Secret named `salesforce-credentials` that DAGs can reference.

## Operational Considerations

**Monitoring:**
- Monitor ESO pod health
- Alert on `ExternalSecret` sync failures
- Track sync metrics (last sync time, error count)

**Troubleshooting:**
```bash
# Check ExternalSecret status
kubectl describe externalsecret salesforce-credentials -n airflow

# Check if Secret was created
kubectl get secret salesforce-credentials -n airflow

# Check ESO logs
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets
```

**Secret Rotation:**
1. Update secret in Azure Key Vault
2. ESO automatically syncs (within refreshInterval)
3. Pods pick up new secret on next restart (or with tools like Reloader)

## Future Considerations

- Could migrate to CSI driver if etcd encryption becomes insufficient
- Could add Reloader to automatically restart pods on secret changes
- Could use ClusterSecretStore for cross-namespace secret sharing
- Could add secret validation webhooks
