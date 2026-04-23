// ============================================================================
// STUDY-ONLY AVM exemplar — Azure AI Search (Tier 2 `landing_zone.mode: avm`).
//
// This file is NOT wired into infra/main.bicep. It shows the canonical
// Azure Verified Modules shape the partner drops into `infra/modules/`
// when replacing the hand-rolled `infra/modules/ai-search.bicep`.
//
// AVM docs: https://github.com/Azure/bicep-registry-modules/tree/main/avm/res/search/search-service
// Module:   br/public:avm/res/search/search-service
//
// Version pin: check version.json in the registry before copying — this
// exemplar targets the major.minor of the moment it was shipped. The
// `ga-sdk-freshness` lint flags drift; bump the version when it does.
//
// Compare against ../modules/ai-search.bicep to see what the partner is
// trading:
//   - AVM handles RBAC role assignments via `roleAssignments:` array.
//   - AVM handles private endpoints + private DNS zone bindings via
//     `privateEndpoints:` array (hand-rolled module has none today).
//   - AVM handles diagnostic settings via `diagnosticSettings:` array.
//   - `disableLocalAuth: true` + system-assigned identity replaces the
//     hand-rolled `authOptions.aadOrApiKey.aadAuthFailureMode: http403`.
// ============================================================================

targetScope = 'resourceGroup'

param name string
param location string
param tags object
param rbacPrincipalId string

// Tier 2 adds private networking. Tier 1 callers pass empty arrays.
param privateEndpointSubnetId string = ''
param privateDnsZoneId string = ''

// Diagnostics land in the workload's own Log Analytics workspace in
// Tier 2; Tier 3 overrides this to the hub's central workspace.
param logAnalyticsWorkspaceId string

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

    // Tier 2: lock public access once a PE subnet is wired.
    publicNetworkAccess: empty(privateEndpointSubnetId) ? 'Enabled' : 'Disabled'

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

    // Private Endpoint binding — empty in Tier 1 fallback.
    privateEndpoints: empty(privateEndpointSubnetId) ? [] : [
      {
        subnetResourceId: privateEndpointSubnetId
        privateDnsZoneGroup: empty(privateDnsZoneId) ? null : {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: privateDnsZoneId
            }
          ]
        }
      }
    ]

    // Diagnostics — every AI ALZ deployment requires this.
    diagnosticSettings: [
      {
        workspaceResourceId: logAnalyticsWorkspaceId
        logCategoriesAndGroups: [
          { categoryGroup: 'allLogs' }
        ]
        metricCategories: [
          { category: 'AllMetrics' }
        ]
      }
    ]
  }
}

output id string = search.outputs.resourceId
output endpoint string = 'https://${name}.search.windows.net'
