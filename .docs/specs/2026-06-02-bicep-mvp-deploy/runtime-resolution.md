# Function Runtime Resolution Summary

## Issue
After completing infrastructure deployment with `azd up`, the Azure Function runtime reported:
- **ServiceUnavailable** errors
- **0 functions loaded**
- **404** on SCM endpoints

## Root Causes Identified

### 1. Missing WEBSITE_CONTENTSHARE Configuration
**Problem**: Y1 Linux Consumption plans require Azure Files storage for function code.
**Solution**: Added to `function-app.bicep`:
```bicep
{
  name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
  value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};...'
}
{
  name: 'WEBSITE_CONTENTSHARE'
  value: toLower(name)
}
```

### 2. WEBSITE_RUN_FROM_PACKAGE Conflict
**Problem**: `WEBSITE_RUN_FROM_PACKAGE=1` bypasses Oryx remote build, preventing dependency installation.
**Solution**: Removed `WEBSITE_RUN_FROM_PACKAGE` setting entirely to enable remote build.

### 3. Remote Build Not Enabled
**Problem**: Python dependencies (azure-functions, azure-storage-blob, etc.) not installed on server.
**Solution**: Added to `function-app.bicep`:
```bicep
{
  name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
  value: '1'
}
{
  name: 'ENABLE_ORYX_BUILD'
  value: '1'
}
```

### 4. Absolute Import Paths
**Problem**: Function code used `from src.functions.*` imports, but `azd deploy` only packages `./src/functions` contents (no `src/` parent).
**Solution**: Changed `function_app.py` to relative imports:
```python
# Before:
from src.functions.batch_start_processing import bp_batch_start_processing

# After:
from batch_start_processing import bp_batch_start_processing
```

## Final State ✅

### Infrastructure
- **11 Azure resources** deployed successfully
- **9 role assignments** configured (7 Function MI + 2 user break-glass)
- **Bicep validation** passes with 0 errors

### Function Runtime
- **4 functions registered**:
  - `batch_start_processing` (httpTrigger)
  - `add_url_embeddings` (httpTrigger)
  - `combine_pages_and_chunknos` (httpTrigger)
  - `batch_push_results` (queueTrigger)
- **Runtime status**: Running, discovering functions correctly
- **Test result**: HTTP invocation returns 500 with `NotImplementedError` ✅ (expected per spec-0001)

### Oryx Remote Build Confirmed
Deployment logs show successful dependency installation:
```
Running pip install...
Successfully installed azure-functions-1.24.0 azure-storage-blob-12.29.0 ...
Deployment successful. deployer = Push-Deployer deploymentPath = Functions App ZipDeploy. Extract zip. Remote build.
```

## Bicep Changes Summary

**File**: `infra/modules/function/function-app.bicep`

**Added**:
1. `WEBSITE_CONTENTAZUREFILECONNECTIONSTRING` - Azure Files connection for Y1 Consumption
2. `WEBSITE_CONTENTSHARE` - File share name for function storage
3. `SCM_DO_BUILD_DURING_DEPLOYMENT='1'` - Enable Oryx remote build
4. `ENABLE_ORYX_BUILD='1'` - Explicitly enable build

**Removed**:
1. `WEBSITE_RUN_FROM_PACKAGE='1'` - Conflicted with remote build

**Code Change**: `src/functions/function_app.py` - Switched to relative imports

## Verification Commands

```powershell
# List registered functions
az rest --method get \
  --uri "/subscriptions/.../providers/Microsoft.Web/sites/func-e7m3pu5wabkp6/functions?api-version=2023-12-01" \
  --query "value[].{name:name, trigger:properties.config.bindings[0].type}"

# Test HTTP function (should return 500 with NotImplementedError until spec-0002)
curl -X POST "https://func-e7m3pu5wabkp6.azurewebsites.net/api/BatchStartProcessing?code=<function-key>"
```

## Amendment for Spec-0003

This resolution adds a **third amendment** to spec-0003:

**Amendment 3 (T0003-12)**: Linux Consumption Y1 requires remote build configuration:
- Removed `WEBSITE_RUN_FROM_PACKAGE` to enable Oryx
- Added `SCM_DO_BUILD_DURING_DEPLOYMENT=1` and `ENABLE_ORYX_BUILD=1`
- Added `WEBSITE_CONTENTSHARE` + connection string for Azure Files storage
- Changed function code to relative imports for deployment compatibility

**Status**: ✅ All infrastructure deployed, all functions registered and callable
