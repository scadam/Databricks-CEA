from __future__ import annotations

import logging

import azure.functions as func
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    TurnContext,
)
from botbuilder.schema import Activity

from app.bot import DatabricksAgentBot
from app.config import MissingConfigurationError, Settings
from app.databricks_client import DatabricksClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


try:
    settings = Settings.from_env()
    if settings.bypass_authentication:
        logger.info("Bypass authentication enabled for local debugging.")
        adapter_settings = BotFrameworkAdapterSettings("", "")
    else:
        adapter_settings = BotFrameworkAdapterSettings(
            settings.microsoft_app_id,
            settings.microsoft_app_password,
        )
    adapter = BotFrameworkAdapter(adapter_settings)
    conversation_state = ConversationState(MemoryStorage())
    databricks_client = DatabricksClient(
        api_key=settings.databricks_token,
        base_url=settings.databricks_base_url,
        model=settings.databricks_model_name,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )
    bot = DatabricksAgentBot(llm_client=databricks_client, system_prompt=settings.system_prompt)
except MissingConfigurationError as exc:  # pragma: no cover - fails fast on cold start
    logger.exception("Critical configuration error: %s", exc)
    raise


async def on_error(context: TurnContext, error: Exception) -> None:
    logger.exception("Unhandled bot error: %s", error)
    await context.send_activity("Something went wrong and I've alerted the team.")
    await conversation_state.delete(context)


adapter.on_turn_error = on_error


@app.function_name(name="messages")
@app.route(route="messages", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    if not req.headers.get("Content-Type", "").startswith("application/json"):
        return func.HttpResponse("Expecting application/json content", status_code=415)

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON payload", status_code=400)

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    await adapter.process_activity(activity, auth_header, bot.on_turn)
    return func.HttpResponse(status_code=201)
