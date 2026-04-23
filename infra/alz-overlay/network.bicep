// Spoke vNet + peering + NSG for Tier 3 alz-integrated deploys.
// Scope: resourceGroup (called from ./main.bicep).

param location string
param tags object
param vnetName string
param vnetAddressPrefix string
param workloadSubnetPrefix string
param hubVnetId string

// Baseline NSG for the workload subnet. Starting rules allow intra-vNet
// traffic both directions and deny inbound from the internet. Hub FW
// egress is enforced via the customer CCoE's route table (UDR bound at
// the subnet) — intentionally not created here because the FW private
// IP is customer-owned.
resource workloadNsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: '${vnetName}-workload-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'Allow-VnetInBound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '*'
        }
      }
      {
        name: 'Deny-InternetInBound'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

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
          networkSecurityGroup: {
            id: workloadNsg.id
          }
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
output workloadNsgId string = workloadNsg.id
