// Spoke vNet + peering for Tier 3 alz-integrated deploys.
// Scope: resourceGroup (called from ./main.bicep).

param location string
param tags object
param vnetName string
param vnetAddressPrefix string
param workloadSubnetPrefix string
param hubVnetId string

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [ vnetAddressPrefix ]
    }
    subnets: [
      {
        name: 'snet-workload'
        properties: {
          addressPrefix: workloadSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

// Peering back to the hub. The hub side must mirror this (customer CCoE owns that).
resource peerToHub 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-05-01' = {
  name: 'to-hub'
  parent: vnet
  properties: {
    allowVirtualNetworkAccess: true
    allowForwardedTraffic: true
    allowGatewayTransit: false
    useRemoteGateways: true
    remoteVirtualNetwork: {
      id: hubVnetId
    }
  }
}

output vnetId string = vnet.id
output workloadSubnetId string = '${vnet.id}/subnets/snet-workload'
