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

@description('Comma-separated list of allowed CORS origins for the FastAPI ALLOWED_ORIGINS env var (e.g. "https://app.contoso.com,https://swa-app.azurestaticapps.net"). Empty (default) means no cross-origin browser calls — the API is server-to-server only. Use "*" for sandbox-only allow-all.')
param allowedOrigins string = ''

// NOTE — Container Apps private endpoint is intentionally NOT wired in
// Tier 3 by this module. The PE sub-resource for
// `Microsoft.App/managedEnvironments` requires the env to be
// vNet-integrated with a dedicated infrastructure subnet (Consumption
// env: /23 minimum), which is larger than the /26 the overlay
// provisions. Tier 3 reachability for the API is expected via:
//   (a) external env + App Gateway/Front Door fronted by the hub FW, or
//   (b) partner enlarges overlay subnet and enables vNet integration
//       via the /configure-landing-zone walkthrough.
// See docs/patterns/azure-ai-landing-zone/README.md "Container App
// reachability" section.

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
            { name: 'ALLOWED_ORIGINS', value: allowedOrigins }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

output fqdn string = 'https://${app.properties.configuration.ingress.fqdn}'
