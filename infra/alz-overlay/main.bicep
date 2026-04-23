// ============================================================================
// SUBSCRIPTION-SCOPE overlay for Tier 3 `landing_zone.mode: alz-integrated`.
//
// Read ./README.md first.
//
// Run BEFORE the workload `infra/main.bicep`. The partner fills in the
// `CHANGEME:` parameter defaults via /configure-landing-zone, then:
//
//   az deployment sub create \
//     --location <region> \
//     --template-file infra/alz-overlay/main.bicep \
//     --parameters infra/alz-overlay/main.parameters.json
//
// Outputs flow into `azd env set` for the workload deploy.
// ============================================================================

targetScope = 'subscription'

@description('Spoke region (must be in the ALZ policy allowed locations).')
param location string

@description('Spoke resource group name (will be created if it does not exist).')
param resourceGroupName string

@description('Tags applied to the spoke RG. Merge with your ALZ tagging policy.')
param tags object = {}

@description('Hub vNet resource ID to peer back to. CHANGEME to the customer hub vNet ID.')
param hubVnetId string

@description('Address space for the spoke vNet. Must not overlap with hub or other spokes.')
param spokeVnetAddressPrefix string

@description('Workload subnet prefix inside the spoke vNet (hosts PEs and Container App integration).')
param workloadSubnetPrefix string

@description('Hub Log Analytics workspace resource ID. CHANGEME to the customer hub LAW ID.')
param hubLogAnalyticsWorkspaceId string

@description('Hub private DNS zone resource IDs (CHANGEME). Used by workload PEs.')
param privateDnsZoneIds object = {
  cognitiveservices: ''  // privatelink.cognitiveservices.azure.com
  openai:            ''  // privatelink.openai.azure.com
  keyvault:          ''  // privatelink.vaultcore.azure.net
  search:            ''  // privatelink.search.windows.net
}

@description('When true, create vNet-links on each hub private DNS zone to the spoke vNet. Requires the deploying identity to have `Private DNS Zone Contributor` on every zone in privateDnsZoneIds. Leave false (default) to have the customer CCoE create the links out-of-band — this is the safer choice in regulated environments where DNS is delegated.')
param createDnsZoneLinks bool = false

// ----------------------------------------------------------------------------
// Spoke resource group
// ----------------------------------------------------------------------------
resource spokeRg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ----------------------------------------------------------------------------
// Spoke vNet + peering + subnet + NSG (deployed into the RG scope)
// ----------------------------------------------------------------------------
module spokeNetwork 'network.bicep' = {
  name: 'spoke-network'
  scope: spokeRg
  params: {
    location: location
    tags: tags
    vnetName: '${resourceGroupName}-vnet'
    vnetAddressPrefix: spokeVnetAddressPrefix
    workloadSubnetPrefix: workloadSubnetPrefix
    hubVnetId: hubVnetId
  }
}

// ----------------------------------------------------------------------------
// Optional: vNet-links on hub DNS zones (opt-in; see createDnsZoneLinks doc).
// Each zone ID is parsed for its (subscriptionId, resourceGroup, name) so
// the link module can be invoked at the zone's own RG scope.
// ----------------------------------------------------------------------------
var zoneIds = [
  { key: 'cognitiveservices', id: privateDnsZoneIds.cognitiveservices }
  { key: 'openai',            id: privateDnsZoneIds.openai }
  { key: 'keyvault',           id: privateDnsZoneIds.keyvault }
  { key: 'search',             id: privateDnsZoneIds.search }
]

module dnsLinks 'dns-zone-link.bicep' = [for z in zoneIds: if (createDnsZoneLinks && !empty(z.id)) {
  name: 'dns-link-${z.key}'
  scope: resourceGroup(split(z.id, '/')[2], split(z.id, '/')[4])
  params: {
    zoneName: split(z.id, '/')[8]
    linkName: '${resourceGroupName}-spoke'
    spokeVnetId: spokeNetwork.outputs.vnetId
    tags: tags
  }
}]

// ----------------------------------------------------------------------------
// Outputs consumed by `azd env set` before the workload deploy
// ----------------------------------------------------------------------------
output resourceGroupName string = spokeRg.name
output workloadSubnetId string = spokeNetwork.outputs.workloadSubnetId
output workloadNsgId string = spokeNetwork.outputs.workloadNsgId
output privateDnsZoneIds object = privateDnsZoneIds
output hubLogAnalyticsWorkspaceId string = hubLogAnalyticsWorkspaceId
