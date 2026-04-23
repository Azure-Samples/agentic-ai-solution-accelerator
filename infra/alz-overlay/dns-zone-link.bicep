// Creates a single Private DNS zone -> vNet link. Scope is the zone's
// parent RG (typically in the hub subscription), so the deploying
// identity needs `Private DNS Zone Contributor` on that RG/zone.
//
// The overlay main.bicep invokes this once per required DNS zone when
// createDnsZoneLinks=true. Leave that flag false to let the customer
// CCoE own DNS vNet-link creation out-of-band, which is common in
// production ALZ deployments.

targetScope = 'resourceGroup'

@description('Full resource ID of the private DNS zone (must live in this scope).')
param zoneName string

@description('Link name (must be unique within the zone).')
param linkName string

@description('Spoke vNet resource ID to link to the zone.')
param spokeVnetId string

@description('Tags applied to the vNet link.')
param tags object = {}

resource zone 'Microsoft.Network/privateDnsZones@2024-06-01' existing = {
  name: zoneName
}

resource link 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: zone
  name: linkName
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: spokeVnetId
    }
  }
}

output linkId string = link.id
