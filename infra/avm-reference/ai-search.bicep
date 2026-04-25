// ============================================================================
// STUDY-ONLY AVM exemplar — Azure AI Search (Tier 2 `landing_zone.mode: avm`).
//
// This file is NOT wired into infra/main.bicep. It is a **drop-in
// replacement** for infra/modules/ai-search.bicep — same param
// signature, same outputs — so a partner can `cp
// infra/avm-reference/ai-search.bicep infra/modules/ai-search.bicep`
// during local iteration without touching main.bicep.
//
// AVM docs: https://github.com/Azure/bicep-registry-modules/tree/main/avm/res/search/search-service
// Module:   br/public:avm/res/search/search-service:0.12.0
//
// What swapping gives you vs the hand-rolled module:
//   - AVM handles RBAC role assignments via `roleAssignments:` array.
//   - AVM supports `privateEndpoints:` + `diagnosticSettings:` arrays
//     (the hand-rolled module has neither today).
//   - `disableLocalAuth: true` + system-assigned identity replaces the
//     hand-rolled `authOptions.aadOrApiKey` block.
//
// What it does NOT give you:
//   - Tier 3 network plumbing (spoke subnet for PE, hub private-DNS
//     zone for `privatelink.search.windows.net`). Those are partner-
//     authored during `mode: alz-integrated` — see H9 and
//     infra/alz-overlay/.
// ============================================================================

targetScope = 'resourceGroup'

// --- drop-in signature (matches infra/modules/ai-search.bicep) ---------------
param name string
param location string
param tags object
param rbacPrincipalId string
param enablePrivateLink bool = false

@description('Tier 3 only. Resource ID of the spoke subnet that hosts the Search PE.')
param peSubnetId string = ''

@description('Tier 3 only. Resource ID of the hub private DNS zone `privatelink.search.windows.net`.')
param privateDnsZoneId string = ''

var deployPrivateEndpoint = !empty(peSubnetId) && !empty(privateDnsZoneId)

module search 'br/public:avm/res/search/search-service:0.12.0' = {
  name: 'search-${name}'
  params: {
    name: name
    location: location
    tags: tags
    sku: 'standard'
    replicaCount: 1
    partitionCount: 1
    semanticSearch: 'standard'

    // Entra-only auth; no admin keys issued. AVM does not require
    // `authOptions` when `disableLocalAuth: true`.
    disableLocalAuth: true
    managedIdentities: {
      systemAssigned: true
    }

    // When Tier 3 flips `enablePrivateLink: true` via
    // main.parameters.alz.json, the data plane goes fail-closed. The
    // partner is responsible for creating the PE + DNS binding via
    // alz-overlay/ or their hub CCoE before the workload is reachable.
    publicNetworkAccess: enablePrivateLink ? 'Disabled' : 'Enabled'

    // Tier 3 PE wiring (drop-in parity with ../modules/ai-search.bicep).
    privateEndpoints: deployPrivateEndpoint ? [
      {
        subnetResourceId: peSubnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: privateDnsZoneId
            }
          ]
        }
      }
    ] : []

    // Replaces the hand-rolled role-assignment resources in
    // ../modules/ai-search.bicep. Role IDs match what seed-search.py
    // needs at provision time:
    //   8ebe5a00... Search Index Data Contributor
    //   7ca78c08... Search Service Contributor
    roleAssignments: [
      {
        principalId: rbacPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
      }
      {
        principalId: rbacPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
      }
    ]
  }
}

// Signature parity: hand-rolled module only exports `endpoint`.
output endpoint string = 'https://${name}.search.windows.net'
