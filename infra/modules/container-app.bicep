param name string
param location string
param tags object
param identityId string
param appInsightsConnectionString string
param foundryEndpoint string
param modelDeploymentName string
param searchEndpoint string

@description('JSON object string mapping accelerator.yaml model slugs to deployed deployment_names. Consumed by src.bootstrap (parses AZURE_AI_FOUNDRY_MODEL_MAP) so each Foundry agent can be bound to its declared slug. Sourced from foundry.bicep `modelMap` output via main.bicep.')
param modelMapJson string = '{}'

@description('Resource ID of the Log Analytics workspace that the Container Apps Environment streams logs to. Required because `appLogsConfiguration.destination=log-analytics` mandates a `logAnalyticsConfiguration` block with `customerId` and `sharedKey`; we look up the workspace via `existing` and pull both off it instead of plumbing two extra params through main.bicep.')
param logAnalyticsId string

@description('When true, the Container App has a public FQDN (Tier 1/2). When false, ingress is internal-only and requires a vNet-integrated environment reachable via private endpoint or hub firewall (Tier 3).')
param externalIngress bool = true

@description('Comma-separated list of allowed CORS origins for the FastAPI ALLOWED_ORIGINS env var (e.g. "https://app.contoso.com,https://swa-app.azurestaticapps.net"). Empty (default) means no cross-origin browser calls — the API is server-to-server only. Use "*" for sandbox-only allow-all.')
param allowedOrigins string = ''

@description('Login server (e.g. acrlabdevxxxx.azurecr.io) of the Azure Container Registry that hosts the api image. Wired into Container App `configuration.registries[]` with the workload UAMI so pulls happen via managed identity (no admin user, no creds in env).')
param containerRegistryLoginServer string

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

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: last(split(logAnalyticsId, '/'))
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${name}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
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
      registries: [
        {
          server: containerRegistryLoginServer
          identity: identityId
        }
      ]
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
            { name: 'AZURE_AI_FOUNDRY_MODEL_MAP', value: modelMapJson }
            { name: 'AZURE_AI_SEARCH_ENDPOINT', value: searchEndpoint }
            { name: 'ALLOWED_ORIGINS', value: allowedOrigins }
          ]
          // Probes gate the deployment readiness signal on the in-app
          // bootstrap (src/bootstrap.py) finishing successfully. The
          // FastAPI lifespan runs Foundry + AI Search bootstrap before
          // serving any route, so a 200 from /healthz proves bootstrap
          // is done. Startup probe budget = periodSeconds × failureThreshold
          // = 10s × 60 = 10 min, which absorbs RBAC role-assignment
          // propagation lag (the longest-tail post-deploy gotcha).
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/healthz', port: 8000 }
              periodSeconds: 10
              failureThreshold: 60
              timeoutSeconds: 5
            }
            {
              type: 'Liveness'
              httpGet: { path: '/healthz', port: 8000 }
              periodSeconds: 30
              failureThreshold: 3
              timeoutSeconds: 5
            }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

output fqdn string = 'https://${app.properties.configuration.ingress.fqdn}'
