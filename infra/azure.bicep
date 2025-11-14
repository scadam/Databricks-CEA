@minLength(4)
@maxLength(20)
@description('Used to generate names for all resources in this file')
param resourceBaseName string

@maxLength(42)
param botDisplayName string

@description('Azure region for the resources')
param location string = resourceGroup().location

@secure()
@description('Databricks personal access token used to call the serving endpoint')
param databricksToken string

@description('Base URL to the Databricks serving endpoints, e.g., https://adb-<workspace>.azuredatabricks.net/serving-endpoints')
param databricksBaseUrl string

@description('Model identifier exposed through the Databricks serving endpoint')
param databricksModelName string = 'databricks-gpt-oss-120b'

@description('Azure Functions hosting plan SKU (Y1 for Consumption, EP* for Premium)')
param functionPlanSku string = 'Y1'

var storageAccountName = toLower('st${uniqueString(resourceGroup().id, resourceBaseName)}')
var functionAppName = toLower(resourceBaseName)
var hostingPlanName = '${resourceBaseName}-plan'
var identityName = resourceBaseName
var appInsightsName = '${resourceBaseName}-ai'

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource hostingPlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: hostingPlanName
  location: location
  kind: 'functionapp'
  sku: {
    name: functionPlanSku
    tier: functionPlanSku == 'Y1' ? 'Dynamic' : 'ElasticPremium'
  }
  properties: {
    reserved: true
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

var storageKey = listKeys(storage.id, '2019-06-01').keys[0].value
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storageKey};EndpointSuffix=${environment().suffixes.storage}'

resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  properties: {
    httpsOnly: true
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
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
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }
        {
          name: 'MicrosoftAppId'
          value: identity.properties.clientId
        }
        {
          name: 'MicrosoftAppType'
          value: 'UserAssignedMSI'
        }
        {
          name: 'MicrosoftAppTenantId'
          value: identity.properties.tenantId
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'DATABRICKS_BASE_URL'
          value: databricksBaseUrl
        }
        {
          name: 'DATABRICKS_MODEL_NAME'
          value: databricksModelName
        }
        {
          name: 'SYSTEM_PROMPT'
          value: 'You are an AI assistant that uses Databricks models to help Microsoft 365 users.'
        }
        {
          name: 'OPENAI_MAX_TOKENS'
          value: '1024'
        }
        {
          name: 'OPENAI_TEMPERATURE'
          value: '0.2'
        }
        {
          name: 'DATABRICKS_TOKEN'
          value: databricksToken
        }
      ]
      ftpsState: 'FtpsOnly'
    }
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
}

module azureBotRegistration './botRegistration/azurebot.bicep' = {
  name: 'Azure-Bot-registration'
  params: {
    resourceBaseName: resourceBaseName
    identityClientId: identity.properties.clientId
    identityResourceId: identity.id
    identityTenantId: identity.properties.tenantId
    botAppDomain: functionApp.properties.defaultHostName
    botDisplayName: botDisplayName
  }
}

output FUNCTION_APP_RESOURCE_ID string = functionApp.id
output BOT_DOMAIN string = functionApp.properties.defaultHostName
output BOT_ID string = identity.properties.clientId
output BOT_TENANT_ID string = identity.properties.tenantId
