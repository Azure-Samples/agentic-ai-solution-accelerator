// ============================================================================
// STUDY-ONLY AVM exemplar — Container Apps Managed Environment + App
// (Tier 2 `landing_zone.mode: avm`).
//
// This file is NOT wired into infra/main.bicep. It shows the canonical
// Azure Verified Modules shape the partner drops into `infra/modules/`
// when replacing the hand-rolled `infra/modules/container-app.bicep`.
//
// Two AVM modules compose the workload:
//   - br/public:avm/res/app/managed-environment   (Container Apps env)
//   - br/public:avm/res/app/container-app         (Container App)
//
// ⚠️  IMPORTANT — ORPHAN WARNING  ⚠️
// The `app/managed-environment` AVM module is currently marked
// **orphaned** in the AVM registry (only security + bug fixes). The
// `app/container-app` module is actively owned. Before adopting this
// exemplar:
//   1. Check https://aka.ms/AVM/OrphanedModules for current status.
//   2. If the orphan state concerns you for a regulated engagement,
//      stay on the hand-rolled ../modules/container-app.bicep until
//      the module is re-adopted, and document that choice in the
//      engagement's landing-zone decision log.
//
// Architectural notes:
// - Container Apps external-vs-internal ingress is controlled at the
//   **managed environment level** via `internal: true`, NOT at the
//   app level. Tier 3 (`landing_zone.mode: alz-integrated`) flips
//   this by setting `externalIngress: false` in main.parameters.alz.json.
// - vNet integration (required when `internal: true`) needs
//   `infrastructureSubnetResourceId` pointing at a /23 delegated
//   subnet in the workload vNet.
// ============================================================================

targetScope = 'resourceGroup'

param name string
param location string
param tags object
param identityId string
param appInsightsConnectionString string
param foundryEndpoint string
param modelDeploymentName string
param searchEndpoint string

// Public (Tier 1/2 default) vs internal-only (Tier 3). When false,
// `infrastructureSubnetResourceId` MUST be provided.
param externalIngress bool = true

// Required when externalIngress = false (Tier 3). Partner supplies
// the /23 subnet resource ID from the workload vNet (Tier 2: local
// vNet; Tier 3: spoke vNet created by infra/alz-overlay/).
param infrastructureSubnetResourceId string = ''

// Log Analytics for diagnostic settings on both env and app (routed via
// `diagnosticSettings` below).
param logAnalyticsWorkspaceId string

// Managed-environment app-logs route to Azure Monitor; diagnostic
// settings (below) land those logs in the provided Log Analytics
// workspace. See AVM README for alternative `destination: 'log-analytics'`
// shape (requires customerId + sharedKey).

module managedEnv 'br/public:avm/res/app/managed-environment:0.13.0' = {
  name: 'cae-${name}'
  params: {
    name: '${name}-env'
    location: location
    tags: tags
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    internal: !externalIngress
    infrastructureSubnetResourceId: empty(infrastructureSubnetResourceId)
      ? null
      : infrastructureSubnetResourceId
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

module app 'br/public:avm/res/app/container-app:0.22.0' = {
  name: 'ca-${name}'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': 'api' })
    environmentResourceId: managedEnv.outputs.resourceId
    managedIdentities: {
      userAssignedResourceIds: [
        identityId
      ]
    }
    // Ingress + scale are configured via AVM's `ingressConfiguration`
    // + `scaleSettings` objects in container-app 0.22.x. Partner fills
    // these in per AVM README when adopting this exemplar. Defaults
    // here leave public ingress enabled on the container app; internal
    // vs external is still governed by `internal` on the env above.
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 3
    }
    diagnosticSettings: [
      {
        workspaceResourceId: logAnalyticsWorkspaceId
        metricCategories: [
          { category: 'AllMetrics' }
        ]
      }
    ]
    containers: [
      {
        name: 'api'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // replaced by azd deploy
        resources: {
          cpu: json('1.0')
          memory: '2Gi'
        }
        env: [
          { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
          { name: 'AZURE_AI_FOUNDRY_ENDPOINT', value: foundryEndpoint }
          { name: 'AZURE_AI_FOUNDRY_MODEL', value: modelDeploymentName }
          { name: 'AZURE_AI_SEARCH_ENDPOINT', value: searchEndpoint }
        ]
      }
    ]
  }
}

output fqdn string = 'https://${app.outputs.fqdn}'
