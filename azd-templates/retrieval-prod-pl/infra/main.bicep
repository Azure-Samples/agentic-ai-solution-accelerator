// STUB — retrieval-prod-pl bundle, prod-privatelink profile.
// Adds private endpoints + restricted tool catalog; otherwise == retrieval-prod.
targetScope = 'resourceGroup'
param environmentName string
param location string = resourceGroup().location
// TODO: PE-enabled Foundry, AI Search, KV, App Config; restricted tool catalog.
