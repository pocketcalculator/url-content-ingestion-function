# Deployment Guide — URL Content Ingestion Function

This guide covers the project file structure, local testing, and step-by-step deployment to Azure.

---

## File Structure

```
url-content-ingestion-function/
├── function_app.py            # Azure Function entry point (HTTP triggers: /scrape-url, /health)
├── scraper.py                 # Web scraping logic (Playwright + BeautifulSoup + Trafilatura)
├── chunker.py                 # Text chunking and search document creation
├── storage.py                 # Azure Blob Storage client (writes to scraped-content container)
├── logger.py                  # Structured JSON logger
├── host.json                  # Azure Functions host configuration (extension bundle v4)
├── requirements.txt           # Python dependencies
├── example_usage.py           # Example HTTP request scripts
├── test_scraper_direct.py     # Direct scraper tests (no Azure Functions runtime required)
│
├── bicep/
│   ├── main.bicep             # Infrastructure-as-code (source of truth)
│   └── main.json              # Compiled ARM template (auto-generated from main.bicep)
│
├── scripts/
│   └── deploy-function.sh     # Shell script wrapper for az CLI deployment
│
└── local.settings.json        # Local dev settings (NOT committed — contains credentials)
```

### What Gets Deployed to Azure

| Resource | Name pattern | Purpose |
|---|---|---|
| Storage Account | `st{uniqueHash}` | Function runtime storage + blob output |
| Blob Container | `scraped-content` | Stores processed JSON documents |
| Log Analytics Workspace | `{appName}-law` | Backend for Application Insights |
| Application Insights | `{appName}-appi` | Telemetry and monitoring |
| App Service Plan | `{appName}-plan` | Consumption (Y1) — pay-per-execution |
| Function App | `{appName}` | Python 3.12 on Linux |

---

## Prerequisites

| Tool | Install |
|---|---|
| Azure CLI | https://learn.microsoft.com/cli/azure/install-azure-cli |
| Azure Functions Core Tools v4 | `npm install -g azure-functions-core-tools@4` |
| Azurite (local storage emulator) | `npm install -g azurite` |
| Python 3.12 | https://www.python.org/downloads/ |

Verify everything is installed:

```bash
az --version
func --version
azurite --version
python3 --version
```

---

## Local Development

### 1. Set up the virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Playwright browsers

```bash
playwright install chromium
```

### 3. Configure local settings

`local.settings.json` is already created and gitignored. For local testing with the storage emulator, it should contain:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "BLOB_CONTAINER_NAME": "scraped-content"
  }
}
```

To test against a real Azure storage account instead, replace `UseDevelopmentStorage=true` with your actual connection string from the Azure portal.

### 4. Start the local storage emulator

```bash
mkdir -p /tmp/azurite
azurite --silent --location /tmp/azurite
```

> Leave this running in a separate terminal.

### 5. Start the Function App locally

```bash
source venv/bin/activate
func start
```

The function will be available at:
- `POST http://localhost:7071/api/scrape-url`
- `GET  http://localhost:7071/api/health`

### 6. Test a request

```bash
curl -X POST http://localhost:7071/api/scrape-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "upload_to_blob": true}'
```

---

## Deploy to Azure

### Option A — Shell script (recommended)

The `scripts/deploy-function.sh` script handles resource group creation, Bicep deployment, and outputs the endpoints in one command.

```bash
chmod +x scripts/deploy-function.sh

./scripts/deploy-function.sh \
  -s <subscription-id> \
  -g <resource-group-name> \
  -l eastus2 \
  -f <function-app-name>
```

**Arguments:**

| Flag | Required | Description |
|---|---|---|
| `-s` | ✅ | Azure subscription ID |
| `-g` | ✅ | Resource group name (created if it doesn't exist) |
| `-l` | ✅ | Azure region (e.g. `eastus2`, `westus3`) |
| `-f` | ✅ | Function App name — must be globally unique |
| `-d` | ❌ | Deployment name (defaults to `function-deploy-<timestamp>`) |

**Example:**

```bash
./scripts/deploy-function.sh \
  -s 00000000-0000-0000-0000-000000000000 \
  -g rg-url-ingestion-prod \
  -l eastus2 \
  -f url-ingestion-fn-prod
```

On success, the script outputs the live endpoints:

```json
{
  "scrapeEndpoint": { "value": "https://url-ingestion-fn-prod.azurewebsites.net/api/scrape-url" },
  "healthEndpoint": { "value": "https://url-ingestion-fn-prod.azurewebsites.net/api/health" },
  "storageAccountNameOut": { "value": "st7f3a9c2d..." },
  "blobContainerNameOut": { "value": "scraped-content" }
}
```

---

### Option B — Azure CLI directly

```bash
# 1. Log in
az login
az account set --subscription <subscription-id>

# 2. Create resource group
az group create \
  --name rg-url-ingestion-prod \
  --location eastus2

# 3. Deploy infrastructure
az deployment group create \
  --resource-group rg-url-ingestion-prod \
  --template-file bicep/main.bicep \
  --parameters \
    functionAppName=url-ingestion-fn-prod \
  --query properties.outputs \
  --output json
```

---

### Deploy the Function Code

After the infrastructure is provisioned, publish the function code:

```bash
source venv/bin/activate

func azure functionapp publish <function-app-name> \
  --python \
  --build remote
```

> `--build remote` installs `requirements.txt` on Azure using Oryx. This is required because some packages (Playwright, lxml) have native dependencies.

---

## Optional Bicep Parameters

The Bicep template accepts these parameters to customize the deployment:

| Parameter | Default | Description |
|---|---|---|
| `functionAppName` | *(required)* | Globally unique Function App name |
| `location` | resource group location | Azure region |
| `pythonVersion` | `3.12` | `3.10`, `3.11`, or `3.12` |
| `storageSkuName` | `Standard_LRS` | Storage redundancy tier |
| `blobContainerName` | `scraped-content` | Output blob container name |
| `logAnalyticsWorkspaceName` | `{appName}-law` | Log Analytics workspace name |
| `appInsightsName` | `{appName}-appi` | Application Insights name |

Pass additional parameters via `--parameters key=value`:

```bash
az deployment group create \
  --resource-group rg-url-ingestion-prod \
  --template-file bicep/main.bicep \
  --parameters \
    functionAppName=url-ingestion-fn-prod \
    pythonVersion=3.12 \
    storageSkuName=Standard_GRS \
    blobContainerName=my-content
```

---

## Regenerating the ARM Template

`bicep/main.json` is auto-generated from `bicep/main.bicep`. After editing the bicep file, rebuild it:

```bash
az bicep build --file bicep/main.bicep --outfile bicep/main.json
```

---

## Teardown

To remove all resources:

```bash
az group delete --name <resource-group-name> --yes --no-wait
```
