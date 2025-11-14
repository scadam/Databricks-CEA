from __future__ import annotations

import logging
from typing import Iterable, Mapping

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import ChannelAccount

from .databricks_client import DatabricksClient, DatabricksClientError

logger = logging.getLogger(__name__)


class DatabricksAgentBot(ActivityHandler):
    """Bot Framework ActivityHandler that forwards prompts to Databricks."""

    def __init__(self, *, llm_client: DatabricksClient, system_prompt: str) -> None:
        super().__init__()
        self._llm_client = llm_client
        self._system_prompt = system_prompt

    async def on_members_added_activity(
        self,
        members_added: Iterable[ChannelAccount],
        turn_context: TurnContext,
    ) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(
                        "Hi! I'm your Databricks-backed copilot. Ask me anything about your data workflows."
                    )
                )

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        user_input = (turn_context.activity.text or "").strip()
        if not user_input:
            await turn_context.send_activity(
                MessageFactory.text("Please send a text prompt and I'll do my best to help!")
            )
            return

        try:
            reply = await self._llm_client.generate_reply(
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_input},
                ]
            )
        except DatabricksClientError as exc:
            logger.exception("Unable to complete Databricks request")
            await turn_context.send_activity(
                MessageFactory.text(
                    "I ran into an issue reaching Databricks just now. Please try again in a moment."
                )
            )
            return

        await turn_context.send_activity(MessageFactory.text(reply))

    async def on_turn(self, turn_context: TurnContext) -> None:  # type: ignore[override]
        """Ensure ActivityHandler processes all activity types."""
        await super().on_turn(turn_context)
