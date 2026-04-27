// Main Bicep entrypoint for the agentic AI accelerator.
// Provisions Foundry project, AI Search, Container App (MI auth), Key Vault,
// App Insights, Log Analytics, and (optionally) private endpoints. The
// scenario plugged into the framework is declared in `accelerator.yaml`;
// Bicep stays scenario-agnostic and tags resources with the scenario id
// supplied by `infra/main.parameters.json` so fleet reporting can roll up
// per-engagement without code changes.
//
// Enforcement notes:
// - No connection strings baked in — workloads authenticate via managed identity.
// - Content filters for the model deployment are set here (never in the portal).
// - App Insights + Log Analytics are the only observability plane.

targetScope = 'resourceGroup'

@description('Short environment name, e.g. dev, stg, prod')
param envName string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Flip publicNetworkAccess to Disabled on Foundry, Search, and Key Vault. Actual private endpoints + DNS wiring are partner-owned for Tier 2 (avm) or come from the overlay for Tier 3 (alz-integrated). See docs/patterns/azure-ai-landing-zone/README.md.')
param enablePrivateLink bool = false

@description('Controls Container App ingress. true = public FQDN (Tier 1/2). false = internal only (Tier 3). Must be false when landing_zone.mode = alz-integrated.')
param externalIngress bool = true

@description('Tier 3 only. Resource ID of the spoke subnet that hosts private endpoints for Key Vault, AI Search, and Foundry. Empty in Tier 1/2; set from the alz-overlay output via `azd env set` before `azd up`.')
param peSubnetId string = ''

@description('Tier 3 only. Hub private DNS zone resource IDs used by workload private endpoints. Keys: cognitiveservices / openai / servicesai (all three needed by Foundry AIServices PE); keyvault (Key Vault PE); search (AI Search PE). Wire these from the alz-overlay output via `azd env set` before `azd up`.')
param privateDnsZoneIds object = {
  cognitiveservices: ''
  openai: ''
  servicesai: ''
  keyvault: ''
  search: ''
}

@description('Comma-separated list of allowed CORS origins for the API (e.g. "https://app.contoso.com,https://swa-app.azurestaticapps.net"). Defaults to the Vite dev server origin (http://localhost:5173) so the bundled reference UI under `patterns/` works against a deployed API out of the box during lab walkthroughs — localhost is never a public origin so this is safe to ship as a default. For production, override via `azd env set ALLOWED_ORIGINS=https://<your-swa>.azurestaticapps.net` before `azd up`. Use "*" only in sandbox subscriptions.')
param allowedOrigins string = 'http://localhost:5173'

// Foundry's AIServices-kind account PE registers THREE DNS suffixes
// (see modules/foundry.bicep comment). Filter the object to the
// applicable keys, drop empties, and pass the resulting array.
var foundryDnsZoneIds = filter(
  [
    privateDnsZoneIds.cognitiveservices
    privateDnsZoneIds.openai
    privateDnsZoneIds.servicesai
  ],
  z => !empty(z)
)

// Tier 3 fail-fast guard. When enablePrivateLink=true, the Tier 3
// PE inputs (peSubnetId + all five hub DNS zone IDs) must be wired in
// via `azd env set` from the alz-overlay outputs before `azd up`. If
// any are missing, azd silently substitutes '' and the module PE
// conditionals are skipped -- yielding public-off + no-PE
// (unreachable, not blocked). Fail-fast here with a self-describing
// deployment name so the error surfaces in the deployment log instead
// of presenting as a confusing runtime connection failure later.
var _tier3InputsMissing = enablePrivateLink && (empty(peSubnetId) || empty(privateDnsZoneIds.keyvault) || empty(privateDnsZoneIds.search) || empty(privateDnsZoneIds.cognitiveservices) || empty(privateDnsZoneIds.openai) || empty(privateDnsZoneIds.servicesai))

resource tier3InputGuard 'Microsoft.Resources/deployments@2022-09-01' = if (_tier3InputsMissing) {
  #disable-next-line no-deployments-resources BCP332
  name: 'TIER3-FAIL-set-AZURE_PE_SUBNET_ID-and-DNS-env-vars'
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        err: {
          type: 'string'
          value: '[reference(\'missing-AZURE_PE_SUBNET_ID-or-AZURE_PRIVATE_DNS_ZONE_env-vars-see-alz-overlay-README\').value]'
        }
      }
    }
  }
}

@description('Resource token for unique naming')
param resourceToken string = uniqueString(subscription().id, resourceGroup().id, envName)

// ---------------------------------------------------------------------------
// Models block: parsed natively from accelerator.yaml at compile time via
// `loadYamlContent`. Bicep reads the manifest directly so `azd up` is a
// single-command operation with no host-side preprocessing or Python hooks.
//
// Contract (also enforced by scripts/accelerator-lint.py::models_block_shape):
//   - Each entry: {slug, deployment_name, model, version, capacity, default?}
//   - Exactly ONE entry has `default: true` and uses `slug: default` (reserved)
//   - When the `models:` block is omitted entirely, fall through to a built-in
//     default (gpt-5-mini @ 2025-08-07, capacity 30) so `azd up` works on a
//     manifest with no `models:` block.
// ---------------------------------------------------------------------------
var manifest = loadYamlContent('../accelerator.yaml')
var modelsBlock = manifest.?models ?? []
var defaultEntries = filter(modelsBlock, m => (m.?default ?? false) == true)
var hasManifestDefault = !empty(defaultEntries)
var defaultModel = hasManifestDefault ? defaultEntries[0] : {
  deployment_name: 'gpt-5-mini'
  model: 'gpt-5-mini'
  version: '2025-08-07'
  capacity: 30
}
var extraModelEntries = filter(modelsBlock, m => (m.?default ?? false) != true)

@description('Scenario id from accelerator.yaml.scenario.id. Flows into the `workload` resource tag so fleet reporting can attribute cost/usage per engagement without Bicep churn when partners swap scenarios.')
param scenarioId string = 'sales-research'

param tags object = {
  'azd-env-name': envName
  workload: '${scenarioId}-accelerator'
}

var workloadIdentityName = 'id-${envName}-${resourceToken}'

module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    name: workloadIdentityName
    location: location
    tags: tags
  }
}

module monitor 'modules/monitor.bicep' = {
  name: 'monitor'
  params: {
    logAnalyticsName: 'log-${envName}-${resourceToken}'
    appInsightsName: 'appi-${envName}-${resourceToken}'
    location: location
    tags: tags
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'kv'
  params: {
    name: 'kv${envName}${take(resourceToken, 10)}'
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
    enablePrivateLink: enablePrivateLink
    peSubnetId: peSubnetId
    privateDnsZoneId: privateDnsZoneIds.keyvault
  }
}

// Resource names are precomputed here (not pulled from module outputs)
// so that downstream `existing` lookups and role-assignment GUIDs are
// determinable at the start of the deployment (BCP120).
var searchName = 'srch-${envName}-${resourceToken}'
// Seed value passed to foundry.bicep's `projectName` param, used INSIDE
// that module to derive the Foundry account name. The Foundry project's
// actual `.name` is set by foundry.bicep's `foundryProjectName` param
// (default 'accelerator-default') — see foundryActualProjectName below.
var foundryAccountSeed = 'fdy-${envName}-${resourceToken}'
// Mirror of foundry.bicep's accountName computation. If that formula
// changes, this mirror must change in lockstep — covered by the
// `bicep build` step in CI.
var foundryAccountName = 'fdy${take(uniqueString(resourceGroup().id, foundryAccountSeed), 12)}'
// Actual Foundry project name (matches foundry.bicep's
// `foundryProjectName` param default). Used by main.bicep's
// `existing` lookup so the project-level connection resource has a
// valid parent at compile time.
var foundryActualProjectName = 'accelerator-default'

module search 'modules/ai-search.bicep' = {
  name: 'search'
  params: {
    name: searchName
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
    enablePrivateLink: enablePrivateLink
    peSubnetId: peSubnetId
    privateDnsZoneId: privateDnsZoneIds.search
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    projectName: foundryAccountSeed
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
    modelName: defaultModel.model
    modelVersion: defaultModel.version
    modelDeploymentName: defaultModel.deployment_name
    modelCapacity: defaultModel.capacity
    extraModelDeployments: extraModelEntries
    enablePrivateLink: enablePrivateLink
    peSubnetId: peSubnetId
    privateDnsZoneIds: foundryDnsZoneIds
  }
}

module containerApp 'modules/container-app.bicep' = {
  name: 'api'
  params: {
    name: 'api-${envName}-${resourceToken}'
    location: location
    tags: tags
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
    appInsightsConnectionString: monitor.outputs.appInsightsConnectionString
    logAnalyticsId: monitor.outputs.logAnalyticsId
    foundryEndpoint: foundry.outputs.projectEndpoint
    foundryProjectName: foundry.outputs.projectName
    foundryOpenAIEndpoint: 'https://${foundryAccountName}.openai.azure.com'
    modelDeploymentName: foundry.outputs.modelDeploymentName
    modelMapJson: string(foundry.outputs.modelMap)
    searchEndpoint: search.outputs.endpoint
    searchResourceId: search.outputs.id
    embeddingDeploymentName: foundry.outputs.embeddingDeploymentName
    foundrySearchConnectionName: searchConnectionName
    externalIngress: externalIngress
    allowedOrigins: allowedOrigins
    containerRegistryLoginServer: registry.outputs.loginServer
  }
}

// ---------------------------------------------------------------------------
// Cross-resource wiring for FoundryIQ over Azure AI Search.
//
// Three things have to be in place for an agent's AzureAISearchTool to
// resolve documents at query-time when its FoundryIQ index uses an AAD
// vectorizer:
//   1. The Foundry project's MI must be able to read the AI Search index
//      ("Search Index Data Reader" on the Search service scope).
//   2. The AI Search service's MI must be able to call Azure OpenAI for
//      query-time vectorization ("Cognitive Services OpenAI User" on the
//      Foundry account scope).
//   3. A project-level connection of category `CognitiveSearch` pointed at
//      the Search service, with `authType: AAD` so callers don't pass keys.
//
// These cross the search/foundry module boundary, so they live inline in
// main.bicep instead of being squeezed into either single-resource module.
// ---------------------------------------------------------------------------
@description('Name of the project-level Cognitive Search connection inside the Foundry project. Bootstrap (FoundryIQ Index asset) references this name when wiring the agent tool.')
param searchConnectionName string = 'accel-search'

// Built-in role IDs (Azure RBAC).
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f' // Search Index Data Reader
var searchIndexDataContribRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
var searchServiceContribRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0' // Search Service Contributor
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
var rbacAdminRoleId = 'f58310d9-a9f6-439a-9e8d-f62e7b41a168' // Role Based Access Control Administrator

// `existing` lookups using compile-time-determinable names so the
// role-assignment GUIDs and connection parent are valid at the start
// of the deployment (BCP120 requires this).
resource searchExisting 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: searchName
}

resource foundryAccountExisting 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: foundryAccountName
}

resource foundryProjectExisting 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: foundryAccountExisting
  name: foundryActualProjectName
}

// (1) Project MI -> Search Index Data Reader on the Search service.
resource projectReadsSearchIndex 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchExisting.id, foundryAccountName, 'projectReadsSearchIndex')
  scope: searchExisting
  properties: {
    principalId: foundry.outputs.projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
  }
  dependsOn: [
    foundry
    search
  ]
}

// (2) Search MI -> Cognitive Services OpenAI User on the Foundry account
// (so the AAD vectorizer in the index can call the embedding deployment).
resource searchCallsAoai 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryAccountExisting.id, searchName, 'searchCallsAoai')
  scope: foundryAccountExisting
  properties: {
    principalId: search.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
  }
  dependsOn: [
    foundry
    search
  ]
}

// (3) Foundry project -> AI Search connection (AAD auth, GA api-version).
resource searchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-12-01' = {
  parent: foundryProjectExisting
  name: searchConnectionName
  properties: {
    authType: 'AAD'
    category: 'CognitiveSearch'
    target: search.outputs.endpoint
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: search.outputs.id
      Location: location
    }
  }
  dependsOn: [
    projectReadsSearchIndex
  ]
}

// (4) Workload MI -> Role Based Access Control Administrator on Search,
// constrained to assigning ONLY the three Search-data roles below.
// Bootstrap (src/bootstrap.py::_grant_agent_search_access) uses this to
// grant each Foundry agent's `instance_identity.principal_id` read access
// to the search service at runtime — that identity is created by Foundry
// when the agent version is created and is not knowable at deploy time.
//
// The condition string follows the ABAC syntax for delegated role
// assignment management; it limits the workload MI to assigning *only*
// the Search Index Data Reader/Contributor + Search Service Contributor
// roles, and only to ServicePrincipal principals. Any other role or
// principal-type request is denied by ARM.
var searchRolesAssignableExpr = '@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {${searchIndexDataReaderRoleId}, ${searchIndexDataContribRoleId}, ${searchServiceContribRoleId}}'
resource workloadAssignsSearchRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchExisting.id, workloadIdentityName, 'workloadAssignsSearchRoles')
  scope: searchExisting
  properties: {
    principalId: identity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', rbacAdminRoleId)
    description: 'Bootstrap-managed: lets the workload MI grant Foundry agent identities access to Search at first run.'
    conditionVersion: '2.0'
    condition: '((!(ActionMatches{\'Microsoft.Authorization/roleAssignments/write\'})) OR (${searchRolesAssignableExpr})) AND ((!(ActionMatches{\'Microsoft.Authorization/roleAssignments/delete\'})) OR (${searchRolesAssignableExpr}))'
  }
  dependsOn: [
    search
    identity
  ]
}

module registry 'modules/acr.bicep' = {
  name: 'registry'
  params: {
    // ACR registry names must be 5-50 chars, lowercase alphanumeric only.
    name: replace('acr${envName}${resourceToken}', '-', '')
    location: location
    tags: tags
    rbacPrincipalId: identity.outputs.principalId
  }
}

output AZURE_AI_FOUNDRY_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_FOUNDRY_ACCOUNT_ENDPOINT string = foundry.outputs.accountEndpoint
output AZURE_AI_FOUNDRY_ACCOUNT_NAME string = foundry.outputs.accountName
output AZURE_AI_FOUNDRY_PROJECT_NAME string = foundry.outputs.projectName
output AZURE_AI_FOUNDRY_MODEL string = foundry.outputs.modelDeploymentName
output AZURE_AI_FOUNDRY_MODEL_MAP object = foundry.outputs.modelMap
output AZURE_AI_FOUNDRY_EMBEDDING_DEPLOYMENT string = foundry.outputs.embeddingDeploymentName
output AZURE_AI_FOUNDRY_RAI_POLICY string = foundry.outputs.raiPolicyName
output AZURE_AI_SEARCH_ENDPOINT string = search.outputs.endpoint
output AZURE_AI_SEARCH_RESOURCE_ID string = search.outputs.id
output AZURE_AI_FOUNDRY_SEARCH_CONNECTION_NAME string = searchConnection.name
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitor.outputs.appInsightsConnectionString
output API_URL string = containerApp.outputs.fqdn
output MANAGED_IDENTITY_CLIENT_ID string = identity.outputs.clientId
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = registry.outputs.name
