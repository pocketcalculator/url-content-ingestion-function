metadata name = 'URL Content Ingestion Function Infrastructure'
metadata description = 'Deploys storage, Application Insights, hosting plan, and a Python Azure Function App.'

targetScope = 'resourceGroup'

/*
 * Compute Parameters
 */

@description('Name of the Azure Function App. Must be globally unique.')
param functionAppName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Python runtime version for the Function App.')
@allowed([
  '3.10'
  '3.11'
  '3.12'
])
param pythonVersion string = '3.11'

/*
 * Monitoring Parameters
 */

@description('Application Insights resource name. Defaults to <functionAppName>-appi.')
param appInsightsName string = '${functionAppName}-appi'

/*
 * Storage Parameters
 */

@description('Storage account SKU name.')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
])
param storageSkuName string = 'Standard_LRS'

/*
 * Variables
 */

var storageAccountName = toLower('st${uniqueString(resourceGroup().id, functionAppName)}')
var hostingPlanName = '${functionAppName}-plan'

/*
 * Resources
 */

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageSkuName
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    IngestionMode: 'ApplicationInsights'
  }
}

resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: hostingPlanName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
    size: 'Y1'
    family: 'Y'
    capacity: 0
  }
  kind: 'functionapp'
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|${pythonVersion}'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${listKeys(storageAccount.id, storageAccount.apiVersion).keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
      ]
    }
  }
}

/*
 * Outputs
 */

@description('Name of the deployed Function App.')
output functionAppNameOut string = functionApp.name

@description('HTTPS endpoint for the scrape route.')
output scrapeEndpoint string = 'https://${functionApp.properties.defaultHostName}/api/scrape-url'

@description('Health endpoint URL.')
output healthEndpoint string = 'https://${functionApp.properties.defaultHostName}/api/health'

@description('System-generated storage account name used by the Function App.')
output storageAccountNameOut string = storageAccount.name
