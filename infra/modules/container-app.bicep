param name string
param location string
param tags object
param identityId string
param appInsightsConnectionString string
param foundryEndpoint string
param modelDeploymentName string
param searchEndpoint string

@description('When true, the Container App has a public FQDN (Tier 1/2). When false, ingress is internal-only and requires a vNet-integrated environment reachable via private endpoint or hub firewall (Tier 3).')
param externalIngress bool = true

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${name}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
    }
    workloadProfiles: [
      { name: 'Consumption', workloadProfileType: 'Consumption' }
    ]
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: externalIngress
        targetPort: 8000
        allowInsecure: false
        transport: 'auto'
      }
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [
        {
          name: 'api'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // replaced by azd deploy
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: [
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'AZURE_AI_FOUNDRY_ENDPOINT', value: foundryEndpoint }
            { name: 'AZURE_AI_FOUNDRY_MODEL', value: modelDeploymentName }
            { name: 'AZURE_AI_SEARCH_ENDPOINT', value: searchEndpoint }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

output fqdn string = 'https://${app.properties.configuration.ingress.fqdn}'
