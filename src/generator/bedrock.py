"""Bedrock-backed GenAI provider (GUARDED).

This path is intentionally inert unless AWS credentials and boto3 are present.
It is included to show the production wiring (propose -> critique -> summarize)
without requiring credentials for the portfolio demo. The local MockProvider is
the default; this provider is only selected when explicitly enabled AND the
environment is configured.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .base import CalcTranslation, GenAIProvider
from .mock import MockProvider

CALC_PROMPT_VERSION = "calc-v1"
VISUAL_PROMPT_VERSION = "visual-v1"
Q_PROMPT_VERSION = "q-topics-v1"


class BedrockProvider(GenAIProvider):
    """Translate via Amazon Bedrock Claude. Falls back to mock rules on any gap.

    NOTE: No network call happens at import time. The boto3 client is created
    lazily and only when :meth:`_invoke` is reached.
    """

    name = "bedrock-claude"

    def __init__(self, model_id: str | None = None, region: str | None = None) -> None:
        self.model_id = model_id or os.environ.get(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._fallback = MockProvider()
        self._client = None

    def _get_client(self):  # pragma: no cover - requires AWS creds
        if self._client is None:
            import boto3  # imported lazily; guarded path only

            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def _invoke(self, prompt: str) -> str:  # pragma: no cover - requires AWS creds
        client = self._get_client()
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        response = client.invoke_model(modelId=self.model_id, body=body)
        payload = json.loads(response["body"].read())
        return payload["content"][0]["text"]

    def translate_calculation(self, calc: dict[str, Any]) -> CalcTranslation:  # pragma: no cover
        # Production: propose -> self-critique -> emit JSON. For the MVP the
        # rule-based result is returned so behavior is deterministic offline.
        result = self._fallback.translate_calculation(calc)
        result.notes.append(f"prompt_version={CALC_PROMPT_VERSION}; model={self.model_id}")
        return result

    def map_visual(self, worksheet: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
        return self._fallback.map_visual(worksheet)

    def generate_q_topics(self, metadata: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
        return self._fallback.generate_q_topics(metadata)
