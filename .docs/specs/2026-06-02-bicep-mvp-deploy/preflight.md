# Pre-Flight Verification (T0003-00)

> Captured: 2026-06-02
> Task: [T0003-00](tasks.md#-t0003-00-pre-flight----verify-aoai-access-and-quota-in-target-subscription)
> Outcome: **PASS** -- spec 0003 is cleared to proceed, with one tech-spec amendment.

## Context

| Field | Value |
|---|---|
| Tenant | `58d1f981-925f-4cc2-8784-1dada5ea620b` |
| Subscription | `f2ebeda7-3df4-471e-9e08-7dd574ced43d` (Visual Studio Enterprise Subscription) |
| Signed-in user | `grschune@8v2048.onmicrosoft.com` |
| Target location | `swedencentral` |

## Checks

### 1. Cognitive Services RP

`az provider show -n Microsoft.CognitiveServices` -> `Registered`. PASS.

### 2. OpenAI account SKU available in swedencentral

```
Kind    Name    ResourceType    Tier
OpenAI  S0      accounts        Standard
```

`S0` account SKU available. PASS.

### 3. `text-embedding-3-small` model availability + SKUs

```
name                    version    skus
----------------------  -------    ----------------------------------
text-embedding-3-small  1          GlobalStandard, DataZoneStandard
```

Model is available. **Regional `Standard` SKU is NOT offered for this model in `swedencentral`** -- only `GlobalStandard` and `DataZoneStandard` are available. This triggers a [tech-spec.md](tech-spec.md) amendment (see below).

### 4. Subscription quota for the model

```
Name                                            CurrentValue    Limit
----------------------------------------------  --------------  -------
OpenAI.GlobalStandard.text-embedding-3-small    0.0             1000.0
OpenAI.DataZoneStandard.text-embedding-3-small  0.0             1000.0
```

1000 K-TPM available on both global and data-zone SKUs, current usage 0. Plenty of headroom for POC capacity 30 (in K-TPM units). PASS.

### 5. Other required resource providers

| Provider | Initial State | Action | Final State |
|---|---|---|---|
| `Microsoft.Search` | Registered | -- | Registered |
| `Microsoft.Storage` | Registered | -- | Registered |
| `Microsoft.KeyVault` | Registered | -- | Registered |
| `microsoft.insights` | Registered | -- | Registered |
| `Microsoft.Web` | NotRegistered | `az provider register` | **Registering** (pending; completes within ~5 min) |
| `Microsoft.EventGrid` | NotRegistered | `az provider register` | Registered |
| `Microsoft.OperationalInsights` | NotRegistered | `az provider register` | Registered |

`Microsoft.Web` will be `Registered` before any `azd up` attempt in T0003-11. Re-check at the start of T0003-11.

### 6. Footprint in `swedencentral`

- No existing AI Search services in `swedencentral`.
- No existing Cognitive Services accounts in `swedencentral`.

No naming or quota collisions expected with the new deploy.

## Tech-spec amendment required

[tech-spec.md](tech-spec.md#target-file-layout-created-by-this-spec) currently specifies for the `embedding-deployment.bicep` module:

> `sku.name = 'Standard'`, `sku.capacity = 30` (POC default).

This is **incorrect for `swedencentral`** -- the only SKUs offered for `text-embedding-3-small` there are `GlobalStandard` and `DataZoneStandard`. The amendment:

- **Default `sku.name = 'GlobalStandard'`** (matches POC intent: global routing, highest TPM ceiling, lowest cost).
- **`sku.capacity = 30`** retained (units are K-TPM; 30 K-TPM = 30,000 TPM, well within the 1000 K-TPM subscription cap).
- Make the SKU name a parameter (`embeddingSkuName`) with default `'GlobalStandard'` so a future ADR can switch to `DataZoneStandard` (EU-only routing) for compliance reasons without a Bicep edit.

This amendment is captured in [tech-spec.md](tech-spec.md) at T0003-03 implementation time. It does not change [spec.md](spec.md) or any decision in [decisions.md](../../product/decisions.md).

## Decision: PROCEED

All gates pass. Spec 0003 is cleared to start [T0003-01](tasks.md#-t0003-01-scaffold-infra-skeleton).
