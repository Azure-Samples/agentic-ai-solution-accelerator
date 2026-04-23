// ============================================================================
// STUDY-ONLY AVM exemplar — Key Vault (Tier 2 `landing_zone.mode: avm`).
//
// This file is NOT wired into infra/main.bicep. It shows the canonical
// Azure Verified Modules shape the partner drops into `infra/modules/`
// when replacing the hand-rolled `infra/modules/key-vault.bicep`.
//
// AVM docs: https://azure.github.io/Azure-Verified-Modules/indexes/bicep/bicep-resource-modules/
// Module:   br/public:avm/res/key-vault/vault
//
// Compare against ../modules/key-vault.bicep to see what the partner is
// trading:
//   - AVM handles RBAC role assignments via `roleAssignments:` array
//     (no hand-rolled role-assignment resource).
//   - AVM handles private endpoints via `privateEndpoints:` array
//     (hand-rolled module has none today).
//   - AVM handles diagnostic settings via `diagnosticSettings:` array.
//   - AVM's default parameters already set soft-delete, purge
//     protection, RBAC-only — matching WAF/CAF baseline without
//     explicit flags.
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

module kv 'br/public:avm/res/key-vault/vault:0.9.0' = {
  name: 'kv-${name}'
  params: {
    name: name
    location: location
    tags: tags
    enablePurgeProtection: true
    enableSoftDelete: true
    enableRbacAuthorization: true

    // Tier 2: lock public access. Entra auth + PE is the only path.
    publicNetworkAccess: empty(privateEndpointSubnetId) ? 'Enabled' : 'Disabled'
    networkAcls: {
      defaultAction: empty(privateEndpointSubnetId) ? 'Allow' : 'Deny'
      bypass: 'AzureServices'
    }

    // Replaces the hand-rolled role-assignment resource in
    // ../modules/key-vault.bicep. 4633458b... = "Key Vault Secrets User".
    roleAssignments: [
      {
        principalId: rbacPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: '4633458b-17de-408a-b874-0445c86b69e6'
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
          { categoryGroup: 'audit' }
          { categoryGroup: 'allLogs' }
        ]
      }
    ]
  }
}

output id string = kv.outputs.resourceId
output uri string = kv.outputs.uri
