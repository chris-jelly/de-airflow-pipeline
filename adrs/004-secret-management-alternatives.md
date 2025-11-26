# ADR-004: Secret Management Alternatives - Reference

**Status**: Informational

**Date**: 2025-11-26

**Purpose**: Reference document comparing different secret management approaches

## Overview

This ADR provides a comparison of various secret management approaches for Airflow on Kubernetes. Our implementation uses **ESO + Pod-Level Mounting** (see ADR-002 and ADR-003), but this document serves as a reference for understanding alternatives.

## Comparison Matrix

| Approach | Security Level | Complexity | Rotation | Cost | Best For |
|----------|---------------|------------|----------|------|----------|
| Manual K8s Secrets | Low | Low | Manual | Low | Dev/Test |
| ESO + Pod-Level (Current) | Medium-High | Medium | Automatic | Low | Production |
| Airflow Secrets Backend | Medium | Medium | Varies | Low-Medium | Airflow-native |
| CSI Secret Driver | High | High | Automatic | Medium | High security |
| Workload Identity | High | Medium | Automatic | Low | Cloud services |

## Detailed Comparison

### 1. Manual Kubernetes Secrets

**Description**: Manually create K8s secrets with `kubectl`

**Security**: Low
- Secrets in etcd (encrypt at rest)
- No sync from source of truth
- Manual rotation prone to errors

**When to use**: Development, testing, quick prototypes

**When not to use**: Production, compliance requirements, multiple environments

---

### 2. External Secrets Operator (ESO) with Pod-Level Mounting

**Description**: ESO syncs from external provider (Azure Key Vault), mounted per-pod

**Security**: Medium-High
- Source of truth in external system (Azure Key Vault)
- Per-pod secret mounting (least privilege)
- Automatic sync and rotation
- Secrets in etcd (mitigated by encryption)

**When to use**: Production environments, GitOps workflows, multiple secret sources

**When not to use**: When secrets must never touch etcd, ultra-high security requirements

**Our choice**: ✅ Implemented (see ADR-002, ADR-003)

---

### 3. Airflow Secrets Backend

**Description**: Airflow pulls secrets from external backends (Vault, AWS Secrets Manager, GCP Secret Manager)

**Configuration example**:
```python
[secrets]
backend = airflow.providers.hashicorp.secrets.vault.VaultBackend
backend_kwargs = {
    "url": "https://vault:8200",
    "token": "...",
}
```

**Security**: Medium
- Secrets in external system
- Airflow components need backend access
- Automatic rotation (depends on backend)
- Doesn't provide pod-level isolation

**Supported backends**:
- HashiCorp Vault
- AWS Secrets Manager
- AWS Systems Manager Parameter Store
- Google Cloud Secret Manager
- Azure Key Vault

**When to use**:
- When using Airflow Connections heavily
- When secrets need to be dynamic (e.g., short-lived tokens)
- When you want Airflow-native secret management

**When not to use**:
- When you need pod-level secret isolation
- When you already have ESO infrastructure
- When you want secrets accessible outside Airflow context

**Trade-offs**:
- ✅ Native Airflow integration
- ✅ Works with Airflow UI/CLI
- ✅ Good for Airflow Connections
- ❌ All Airflow components can access secrets
- ❌ Doesn't solve least privilege at pod level
- ❌ Adds dependency on external service availability during task execution

---

### 4. Secrets Store CSI Driver

**Description**: Mount secrets directly from external provider into pods using CSI driver

**Configuration example**:
```yaml
volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      volumeAttributes:
        secretProviderClass: "azure-secrets"
volumeMounts:
  - name: secrets-store
    mountPath: "/mnt/secrets"
    readOnly: true
```

**Security**: High
- Secrets never stored in Kubernetes etcd
- Direct mount from external provider
- Automatic rotation (provider dependent)
- Can sync to K8s secrets optionally

**Supported providers**:
- Azure Key Vault
- AWS Secrets Manager
- GCP Secret Manager
- HashiCorp Vault

**When to use**:
- High security requirements (healthcare, finance, government)
- Compliance requiring secrets never in K8s
- Need memory-only secret mounting

**When not to use**:
- When ESO is sufficient for security needs
- When you want simpler setup
- When debugging/troubleshooting complexity is a concern

**Trade-offs**:
- ✅ Highest security (secrets not in etcd)
- ✅ Direct mount from source
- ✅ Memory-only mounting available
- ❌ More complex setup
- ❌ CSI driver must be healthy
- ❌ Platform-specific configuration
- ❌ Harder to debug issues

---

### 5. Workload Identity

**Description**: Use cloud provider identity federation to eliminate static credentials

**AWS (IRSA)**:
```yaml
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123:role/airflow-sa
```

**GCP (Workload Identity)**:
```yaml
serviceAccount:
  annotations:
    iam.gke.io/gcp-service-account: airflow@project.iam.gserviceaccount.com
```

**Azure (Workload Identity)**:
```yaml
serviceAccount:
  annotations:
    azure.workload.identity/client-id: "12345678-1234-1234-1234-123456789012"
```

**Security**: High
- No static credentials
- Automatic rotation by cloud provider
- Native IAM integration
- Audit trail in cloud IAM

**When to use**:
- Accessing cloud services (S3, RDS, Cloud Storage, etc.)
- Cloud-native applications
- Want to eliminate credential management for cloud resources

**When not to use**:
- Third-party SaaS (Salesforce, APIs)
- On-premises resources
- Services without cloud IAM integration

**Trade-offs**:
- ✅ No credential management for cloud resources
- ✅ Native cloud integration
- ✅ Fine-grained IAM permissions
- ✅ Automatic rotation
- ❌ Cloud-specific
- ❌ Doesn't work for third-party services
- ❌ Requires cloud provider setup

**Use with our approach**: ✅ Complementary
- Use workload identity for PostgreSQL (cloud DB)
- Use ESO + pod-level mounting for Salesforce (third-party)

---

## Combination Strategies

### Strategy 1: ESO + Workload Identity (Recommended)
- **ESO** for third-party service credentials (Salesforce, APIs)
- **Workload Identity** for cloud resource access (PostgreSQL on Azure, S3, etc.)
- Best of both worlds

### Strategy 2: CSI + Workload Identity (High Security)
- **CSI Driver** for ultra-sensitive credentials
- **Workload Identity** for cloud resources
- Maximum security, higher complexity

### Strategy 3: Airflow Backend + Workload Identity
- **Airflow Secrets Backend** for Airflow-managed secrets
- **Workload Identity** for cloud resources
- Good for Airflow-centric workflows

## Decision Factors

**Choose ESO when:**
- ✅ Need GitOps workflows
- ✅ Multiple secret sources
- ✅ Standard K8s secrets acceptable
- ✅ Want simplicity with good security

**Choose CSI Driver when:**
- ✅ Secrets must never touch etcd
- ✅ Compliance requirements
- ✅ Can handle complexity
- ✅ Need highest security level

**Choose Airflow Backend when:**
- ✅ Using Airflow Connections heavily
- ✅ Want Airflow-native approach
- ✅ Need dynamic secrets
- ✅ Pod-level isolation not critical

**Choose Workload Identity when:**
- ✅ Accessing cloud services
- ✅ Want to eliminate credential management
- ✅ Cloud-native architecture
- ✅ Works with your resources

## Migration Path

If security requirements increase:

1. **Current** (ESO + Pod-Level): Production ready ✅
2. **Add** Workload Identity for cloud resources
3. **Migrate** to CSI if etcd encryption insufficient
4. **Add** HSM-backed secrets if needed
5. **Implement** runtime secret scanning

Each step adds security without discarding previous work.

## References

- External Secrets Operator: https://external-secrets.io/
- Secrets Store CSI Driver: https://secrets-store-csi-driver.sigs.k8s.io/
- Airflow Secrets Backend: https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/
- AWS IRSA: https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html
- GCP Workload Identity: https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity
- Azure Workload Identity: https://azure.github.io/azure-workload-identity/
