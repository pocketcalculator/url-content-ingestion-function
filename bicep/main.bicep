metadata name = 'URL Content Ingestion Function Infrastructure'
metadata description = 'Deploys storage, blob container, Log Analytics, Application Insights, hosting plan, and a Python Azure Function App.'

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
param pythonVersion string = '3.12'

/*
 * Monitoring Parameters
 */

@description('Log Analytics workspace name. Defaults to <functionAppName>-law.')
param logAnalyticsWorkspaceName string = '${functionAppName}-law'

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

@description('Blob container name for scraped content documents.')
param blobContainerName string = 'scraped-content'

/*
 * Variables
 */

var storageAccountName = toLower('st${uniqueString(resourceGroup().id, functionAppName)}')
var hostingPlanName = '${functionAppName}-plan'
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

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

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource scrapedContentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: blobContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
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
          value: storageConnectionString
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
        {
          // Enables pip install of requirements.txt during remote build
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }
        {
          // Required for Oryx-based remote build on Linux consumption plan
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
        {
          name: 'BLOB_CONTAINER_NAME'
          value: blobContainerName
        }
      ]
    }
  }
  dependsOn: [
    scrapedContentContainer
  ]
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

@description('System-generated storage account name.')
output storageAccountNameOut string = storageAccount.name

@description('Blob container name for scraped content.')
output blobContainerNameOut string = scrapedContentContainer.name

@description('Log Analytics workspace resource ID.')
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
