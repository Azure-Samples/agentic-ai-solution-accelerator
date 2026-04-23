param name string
param location string
param tags object
param rbacPrincipalId string

@description('When true, flips publicNetworkAccess to Disabled. NOTE: disabled does NOT by itself mean the vault is reachable — private endpoints + DNS wiring are required for Tier 3 (alz-integrated). See docs/patterns/azure-ai-landing-zone/README.md.')
param enablePrivateLink bool = false

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
    publicNetworkAccess: enablePrivateLink ? 'Disabled' : 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: enablePrivateLink ? 'Deny' : 'Allow'
    }
  }
}

// Key Vault Secrets User built-in role
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, rbacPrincipalId, kvSecretsUserRoleId)
  scope: kv
  properties: {
    principalId: rbacPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
  }
}

output id string = kv.id
output uri string = kv.properties.vaultUri
