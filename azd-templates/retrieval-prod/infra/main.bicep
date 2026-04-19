// STUB — Phase A. retrieval-prod bundle, prod-standard profile.
// No side-effect tools; no private link. Public network, production SKUs.
// Full impl ships with baseline v1.0.
targetScope = 'resourceGroup'
param environmentName string
param location string = resourceGroup().location
// TODO: Foundry + AI Search + Container Apps + KV + App Config + App Insights + alerts/Action Groups.
