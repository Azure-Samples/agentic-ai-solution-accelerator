// azd-templates/sandbox-only/infra/main.bicep
// STUB — Phase A. Full implementation ships with baseline v1.0.
// Intent: deploys Foundry project + Container Apps + App Insights + KV in sandbox profile
// with auto-teardown tag + budget alert + connector allow-list.

targetScope = 'resourceGroup'

@description('Environment name (from azd).')
param environmentName string

@description('Deployment region.')
param location string = resourceGroup().location

@description('Sandbox profile: dev-sandbox (dedicated isolation) or guided-demo (fallback).')
@allowed([ 'dev-sandbox', 'guided-demo' ])
param profile string = 'dev-sandbox'

@description('Auto-teardown target date (ISO 8601). Enforced by Azure Policy.')
param autoTeardownAt string

// TODO (Phase C): invoke shared modules under delivery-assets/bicep/modules/
//   - foundry-project, ai-search, container-apps, kv, app-config, app-insights
//   - sandbox-profile enforcement (policy deny-assignments, custom RBAC role)
//   - connector allow-list, budget alert, watermark

output profile string = profile
output autoTeardownAt string = autoTeardownAt
