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

// Tier 3: private endpoint + DNS zone group. Created only when both
// peSubnetId and privateDnsZoneId are passed in. Tier 1/2 defaults
// leave these empty so the resource is not instantiated.
resource kvPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = if (deployPrivateEndpoint) {
  name: '${name}-pe'
  location: location
  tags: tags
  properties: {
    subnet: { id: peSubnetId }
    privateLinkServiceConnections: [
      {
        name: '${name}-plsc'
        properties: {
          privateLinkServiceId: kv.id
          groupIds: [ 'vault' ]
        }
      }
    ]
  }
}

resource kvPrivateEndpointDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = if (deployPrivateEndpoint) {
  parent: kvPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'default'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

output id string = kv.id
output uri string = kv.properties.vaultUri
