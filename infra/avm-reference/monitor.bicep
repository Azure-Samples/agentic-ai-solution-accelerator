// ============================================================================
// STUDY-ONLY AVM exemplar — Log Analytics + Application Insights
// (Tier 2 `landing_zone.mode: avm`).
//
// This file is NOT wired into infra/main.bicep. It shows the canonical
// Azure Verified Modules shape the partner drops into `infra/modules/`
// when replacing the hand-rolled `infra/modules/monitor.bicep`.
//
// Two AVM modules compose the observability plane:
//   - br/public:avm/res/operational-insights/workspace   (Log Analytics)
//   - br/public:avm/res/insights/component               (App Insights)
//
// Both are active / well-maintained. Version pins: check version.json
// in the registry before copying. `ga-sdk-freshness` flags drift.
//
// Compare against ../modules/monitor.bicep — the AVM versions set
// WAF-aligned defaults (retention, daily quota, workspace-based
// ingestion) that the hand-rolled module expresses only partially.
// ============================================================================

targetScope = 'resourceGroup'

param logAnalyticsName string
param appInsightsName string
param location string
param tags object

// Tier 3 overrides this to bind App Insights to the hub's central
// workspace instead of the local one. Tier 2 leaves it empty and
// uses the local workspace created below.
param hubLogAnalyticsWorkspaceId string = ''

module law 'br/public:avm/res/operational-insights/workspace:0.15.0' = {
  name: 'law-${logAnalyticsName}'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
    dataRetention: 30
    skuName: 'PerGB2018'
  }
}

// App Insights binds to the hub workspace when Tier 3 passes one in;
// otherwise it binds to the local workspace just created.
module ai 'br/public:avm/res/insights/component:0.7.0' = {
  name: 'ai-${appInsightsName}'
  params: {
    name: appInsightsName
    location: location
    tags: tags
    workspaceResourceId: empty(hubLogAnalyticsWorkspaceId)
      ? law.outputs.resourceId
      : hubLogAnalyticsWorkspaceId
    kind: 'web'
    applicationType: 'web'
    disableLocalAuth: true
  }
}

output logAnalyticsId string = law.outputs.resourceId
output appInsightsConnectionString string = ai.outputs.connectionString
