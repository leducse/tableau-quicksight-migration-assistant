"""Select a GenAI provider.

Default is the fully local MockProvider. The Bedrock path is opt-in via
``GENAI_PROVIDER=bedrock`` (or ``use_bedrock=True``) AND requires boto3 to be
importable; otherwise we transparently fall back to the mock so the loop never
fails for lack of AWS credentials.
"""

from __future__ import annotations

import os

from .base import GenAIProvider
from .mock import MockProvider


def get_provider(use_bedrock: bool | None = None) -> GenAIProvider:
    if use_bedrock is None:
        use_bedrock = os.environ.get("GENAI_PROVIDER", "mock").lower() == "bedrock"

    if not use_bedrock:
        return MockProvider()

    try:
        import boto3  # noqa: F401

        from .bedrock import BedrockProvider

        return BedrockProvider()
    except Exception:
        # Guarded: no boto3 / no creds -> stay fully local.
        return MockProvider()
