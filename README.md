# Databricks Custom Engine Agent (Python on Azure Functions)

This project hosts a Microsoft 365 custom engine agent implemented in **Python** and delivered through an **Azure Functions** app that exposes the Bot Framework `/api/messages` endpoint. Instead of OpenAI, the agent uses **Databricks Serving Endpoints** via their OpenAI-compatible API surface to generate responses.

## Architecture snapshot

- **Runtime**: Azure Functions (Linux, Python 3.11) with the v2 programming model and a single HTTP-triggered function.
- **Bot Framework**: `botbuilder-core` `CloudAdapter` wired to `AzureFunctionsHandler` for Teams / Copilot traffic.
- **LLM provider**: Databricks OpenAI-compatible endpoint configured through `DATABRICKS_BASE_URL`, `DATABRICKS_MODEL_NAME`, and a PAT stored as `DATABRICKS_TOKEN`.
- **Infrastructure-as-code**: `infra/azure.bicep` now provisions a Storage Account, Linux Consumption plan, Function App, Application Insights, and the Bot registration wired to the Function host name.
- **Configuration**: `app/config.py` centralizes required environment variables, while `local.settings.sample.json` documents local defaults.
- **Testing**: `pytest`-based unit tests live under `tests/` and validate the strict config contract.

## Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local?tabs=python)
- [Microsoft 365 Agents Toolkit](https://aka.ms/teams-toolkit) (VS Code extension or CLI)
- An Azure subscription with permission to create Function Apps, storage, and bot registrations
- A Databricks personal access token and serving endpoint URL

## Local development

1. Copy `local.settings.sample.json` to `local.settings.json` and populate the placeholders. Use `UseDevelopmentStorage=true` for `AzureWebJobsStorage` or point to a live storage account.
2. Install dependencies into a virtual environment:

	```powershell
	python -m venv .venv
	.venv\Scripts\Activate.ps1
	python -m pip install -r requirements-dev.txt
	```

3. Run unit tests to verify the setup:

	```powershell
	python -m pytest
	```

4. Start the Azure Functions host (the Teams Toolkit tasks labeled **Start application** call the same command):

	```powershell
	func start
	```

### Environment variables of interest

| Name | Purpose |
| --- | --- |
| `MicrosoftAppId` / `MicrosoftAppType` / `MicrosoftAppTenantId` | Values created by Teams Toolkit during provision so Bot Framework can authenticate your bot |
| `DATABRICKS_BASE_URL` | Base URL to your serving endpoints, e.g., `https://adb-<workspace>.azuredatabricks.net/serving-endpoints` |
| `DATABRICKS_MODEL_NAME` | Model identifier exposed by Databricks |
| `DATABRICKS_TOKEN` | Databricks PAT – store as `SECRET_DATABRICKS_TOKEN` in `.env.*.user` files so it flows into deployment |
| `SYSTEM_PROMPT`, `OPENAI_MAX_TOKENS`, `OPENAI_TEMPERATURE` | Optional tuning knobs with safe defaults |

## Deployment flow

`m365agents.yml` and its environment overrides run the following pipeline when you execute `teamsapp provision` + `teamsapp deploy`:

1. Provision Azure resources via Bicep (Storage Account, Consumption plan, User Assigned Managed Identity, Function App, Application Insights, Bot registration).
2. Install Python dependencies into `.python_packages/lib/site-packages` for zip deployment.
3. Zip the Azure Functions project (respecting `.webappignore` / `.funcignore`) and publish it to the Function App using `azureFunctions/zipDeploy`.
4. Update the Teams / Copilot manifest with the new bot ID and domain.

## Repository map

| Path | Description |
| --- | --- |
| `function_app.py` | Azure Functions entry point using the Python v2 programming model |
| `app/` | Bot + Databricks client modules |
| `tests/` | `pytest` suite |
| `infra/` | Bicep templates for Azure resources |
| `appPackage/` | Teams / Copilot manifest template |
| `env/` | Microsoft 365 Agents Toolkit environment files |

## Databricks connectivity

`app/databricks_client.py` wraps the official `openai` package configured with your Databricks base URL. All requests include:

```python
response = client.chat.completions.create(
	 model=settings.databricks_model_name,
	 messages=[{"role": "system", "content": settings.system_prompt}, {"role": "user", "content": prompt}],
	 max_tokens=settings.max_tokens,
	 temperature=settings.temperature,
)
```

The PAT is never logged or stored in source control; store it with the `SECRET_` prefix inside `env/.env.<environment>.user` so the Toolkit masks it automatically.

## Troubleshooting tips

- Run `func azure functionapp publish <app-name>` locally if you prefer the Functions tooling over the Toolkit pipeline.
- Ensure the Databricks workspace firewall allows outbound traffic from Azure Functions, or configure a VNet integration.
- When testing locally against the Bot Framework Emulator, populate `MicrosoftAppPassword` with the client secret created in `m365agents.local.yml`.

## Next steps

- Expand the pytest suite to cover the Databricks client with mocked responses.
- Add Application Insights telemetry exporters once the resource is provisioned.
- Gate deployments with GitHub Actions using the same Teams Toolkit commands for parity.
