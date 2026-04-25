// ============================================================================
// STUDY-ONLY AVM exemplar — Container Apps Managed Environment + App
// (Tier 2 `landing_zone.mode: avm`).
//
// This file is NOT wired into infra/main.bicep. It is a **drop-in
// replacement** for infra/modules/container-app.bicep — same param
// signature, same outputs — so a partner can `cp
// infra/avm-reference/container-app.bicep infra/modules/container-app.bicep`
// during local iteration without touching main.bicep.
//
// Two AVM modules compose the workload:
//   - br/public:avm/res/app/managed-environment:0.13.0
//   - br/public:avm/res/app/container-app:0.22.0
//
// ⚠️  IMPORTANT — ORPHAN WARNING  ⚠️
// The `app/managed-environment` AVM module is currently marked
// **orphaned** in the AVM registry (security + bug fixes only). The
// `app/container-app` module is actively owned. Before adopting this
// exemplar in a regulated / Microsoft-branded engagement:
//   1. Check https://aka.ms/AVM/OrphanedModules for current status.
//   2. If the orphan state concerns you, stay on the hand-rolled
//      ../modules/container-app.bicep until the module is re-adopted,
//      and document that choice in the engagement's landing-zone
//      decision log.
// ============================================================================

targetScope = 'resourceGroup'

// --- drop-in signature (matches infra/modules/container-app.bicep) -----------
param name string
param location string
param tags object
param identityId string
param appInsightsConnectionString string
param foundryEndpoint string
param modelDeploymentName string
param searchEndpoint string
param externalIngress bool = true

module managedEnv 'br/public:avm/res/app/managed-environment:0.13.0' = {
  name: 'cae-${name}'
  params: {
    name: '${name}-env'
    location: location
    tags: tags
    // Managed-env app-logs route to Azure Monitor. See AVM README for
    // the alternative `destination: 'log-analytics'` shape (requires
    // customerId + sharedKey).
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    // `internal: true` keeps the env off the public internet. Tier 3
    // workloads require this AND a vNet-integrated infrastructure
    // subnet. The hand-rolled module does not currently support
    // internal mode; the AVM exemplar does, but the partner must
    // thread an `infrastructureSubnetResourceId` through main.bicep
    // when adopting.
    internal: !externalIngress
    // AVM `app/managed-environment:0.13.0` defaults
    // `publicNetworkAccess` to **Disabled**. Without an explicit flip
    // here, `externalIngress: true` would silently produce an
    // unreachable environment. Bind the env's public-access flag to
    // the same knob the app ingress uses.
    publicNetworkAccess: externalIngress ? 'Enabled' : 'Disabled'
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
    // Ingress config — app-level controls matter even when the env is
    // internal. `ingressExternal: false` + `env.internal: true` together
    // yield a fully-internal Container App. External env + external app
    // is the Tier 1/2 default. Fronting Container Apps with App Gateway
    // requires an **internal** env with infrastructure-subnet vNet
    // integration (see Azure Container Apps networking docs) — that is
    // Tier 3 territory, not Tier 2.
    activeRevisionsMode: 'Single'
    ingressExternal: externalIngress
    ingressTargetPort: 8000
    ingressAllowInsecure: false
    ingressTransport: 'auto'
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 3
    }
    containers: [
      {
        name: 'api'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // replaced by `azd deploy`
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

// Signature parity: hand-rolled module exports `fqdn`.
output fqdn string = 'https://${app.outputs.fqdn}'
