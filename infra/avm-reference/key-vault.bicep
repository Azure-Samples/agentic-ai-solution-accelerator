// ============================================================================
// STUDY-ONLY AVM exemplar — Key Vault (Tier 2 `landing_zone.mode: avm`).
//
// This file is NOT wired into infra/main.bicep. It is a **drop-in
// replacement** for infra/modules/key-vault.bicep — same param
// signature, same outputs — so a partner can
// `cp infra/avm-reference/key-vault.bicep infra/modules/key-vault.bicep`
// during vibecoding without touching main.bicep.
//
// AVM module: br/public:avm/res/key-vault/vault:0.9.0
//
// What you trade by adopting the AVM shape:
//   - RBAC role assignments move to the AVM `roleAssignments:` array
//     (no separate Microsoft.Authorization/roleAssignments resource).
//   - AVM defaults already set soft-delete, purge protection, RBAC-only
//     — matching WAF/CAF baseline without explicit flags.
//
// What "drop-in" does NOT mean (per infra/avm-reference/README.md):
//   - Private endpoints + private-DNS zone binding — AVM exposes a
//     `privateEndpoints:` array, but wiring subnet + zone IDs through
//     main.bicep is Tier 3 (alz-overlay) work, not Tier 2.
//   - Diagnostic settings to a hub-central Log Analytics workspace —
//     also Tier 3. The hand-rolled module does not emit diagnostics
//     today; the exemplar matches that for drop-in parity.
// ============================================================================

targetScope = 'resourceGroup'

param name string
param location string
param tags object
param rbacPrincipalId string

@description('When true, flips publicNetworkAccess to Disabled. NOTE: disabled does NOT by itself mean the vault is reachable — private endpoints + DNS wiring are required for Tier 3 (alz-integrated). See docs/patterns/azure-ai-landing-zone/README.md.')
param enablePrivateLink bool = false

@description('Tier 3 only. Resource ID of the spoke subnet that hosts the vault PE. Leave empty in Tier 1/2. When set together with privateDnsZoneId, a private endpoint + DNS zone group are created.')
param peSubnetId string = ''

@description('Tier 3 only. Resource ID of the hub private DNS zone `privatelink.vaultcore.azure.net`. Leave empty in Tier 1/2.')
param privateDnsZoneId string = ''

var deployPrivateEndpoint = !empty(peSubnetId) && !empty(privateDnsZoneId)

module kv 'br/public:avm/res/key-vault/vault:0.9.0' = {
  name: 'kv-${name}'
  params: {
    name: name
    location: location
    tags: tags
    // --- explicit overrides to match hand-rolled behavior ---
    // AVM vault:0.9.0 defaults `sku` to 'premium'; the hand-rolled
    // module uses 'standard'. Drop-in parity => pin to 'standard'.
    sku: 'standard'
    // AVM vault:0.9.0 defaults these three flags to `true`; the
    // hand-rolled module leaves them unset (ARM default `false`).
    // Override to keep swap behavior-identical.
    enableVaultForDeployment: false
    enableVaultForTemplateDeployment: false
    enableVaultForDiskEncryption: false
    // AVM vault:0.9.0 defaults `enableTelemetry` to `true`, which
    // deploys an extra `Microsoft.Resources/deployments` telemetry
    // resource. The hand-rolled module deploys nothing of the sort;
    // disable it to match.
    enableTelemetry: false
    // --- flags the hand-rolled module also enables ---
    enablePurgeProtection: true
    enableSoftDelete: true
    enableRbacAuthorization: true

    publicNetworkAccess: enablePrivateLink ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: enablePrivateLink ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }

    // Tier 3: bind the vault to a spoke subnet PE + hub DNS zone. The
    // AVM `privateEndpoints:` array produces the same underlying
    // `Microsoft.Network/privateEndpoints` + `privateDnsZoneGroups`
    // resources that the hand-rolled module creates directly. Empty
    // array in Tier 1/2 is a no-op.
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

    // Replaces the hand-rolled role-assignment resource in
    // ../modules/key-vault.bicep. 4633458b... = "Key Vault Secrets User".
    roleAssignments: [
      {
        principalId: rbacPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: '4633458b-17de-408a-b874-0445c86b69e6'
      }
    ]
  }
}

// Signature parity with ../modules/key-vault.bicep.
output id string = kv.outputs.resourceId
output uri string = kv.outputs.uri
