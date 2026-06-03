"""LLM helper trimmed to embedding-only operations for ``doc-ingest-pipeline``.

Ported and modified from
``code/backend/batch/utilities/helpers/llm_helper.py`` of
``Azure-Samples/chat-with-your-data-solution-accelerator`` at commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``.

Modifications per spec-0002 (MODIFY entry in component-reuse-map):

* **Drops** all chat-completion paths (``get_llm``, ``get_streaming_llm``,
  ``get_chat_completion``, ``get_chat_completion_with_functions``,
  ``get_sk_chat_completion_service``, ``get_sk_service_settings``,
  ``get_ml_client``) -- they belong to the parent's chat/orchestration
  surface, excluded by DEC-001.
* **Drops** the ``langchain_openai`` / ``langchain.callbacks`` /
  ``semantic_kernel`` / ``azure.ai.ml`` imports that those chat paths
  required. This removes heavy ML dependencies from the deployable.
* ``get_embedding_model`` is kept but reimplemented as a lightweight
  proxy over the OpenAI SDK (no LangChain). It exposes the single method
  callers actually use: ``embed_query(text) -> List[float]``.
* ``generate_embeddings`` is kept verbatim (the ingestion hot path).
* ``get_chat_completion`` raises ``NotImplementedError`` so the
  image-captioning path in ``push_embedder`` produces a clear error if it
  is ever invoked despite ``USE_ADVANCED_IMAGE_PROCESSING=False``
  (see spec-0002 Out of Scope / Phase 4).
"""

from __future__ import annotations

import logging
from typing import List, Union

from openai import AzureOpenAI

from .env_helper import EnvHelper

logger = logging.getLogger(__name__)


class _EmbeddingModelProxy:
    """Minimal stand-in for ``langchain_openai.AzureOpenAIEmbeddings``.

    Only ``embed_query`` is consumed downstream (``AzureSearchHelper`` uses
    it to detect the embedding dimension once on cold start).
    """

    def __init__(self, llm_helper: "LLMHelper") -> None:
        self._llm_helper = llm_helper

    def embed_query(self, text: str) -> List[float]:
        return self._llm_helper.generate_embeddings(text)


class LLMHelper:
    def __init__(self):
        logger.info("Initializing LLMHelper (embedding-only)")
        self.env_helper: EnvHelper = EnvHelper()
        self.auth_type_keys = self.env_helper.is_auth_type_keys()
        self.token_provider = self.env_helper.AZURE_TOKEN_PROVIDER

        if self.auth_type_keys:
            self.openai_client = AzureOpenAI(
                azure_endpoint=self.env_helper.AZURE_OPENAI_ENDPOINT,
                api_version=self.env_helper.AZURE_OPENAI_API_VERSION,
                api_key=self.env_helper.OPENAI_API_KEY,
            )
        else:
            self.openai_client = AzureOpenAI(
                azure_endpoint=self.env_helper.AZURE_OPENAI_ENDPOINT,
                api_version=self.env_helper.AZURE_OPENAI_API_VERSION,
                azure_ad_token_provider=self.token_provider,
            )

        self.llm_model = self.env_helper.AZURE_OPENAI_MODEL
        self.llm_max_tokens = (
            int(self.env_helper.AZURE_OPENAI_MAX_TOKENS)
            if self.env_helper.AZURE_OPENAI_MAX_TOKENS != ""
            else None
        )
        self.embedding_model = self.env_helper.AZURE_OPENAI_EMBEDDING_MODEL

        logger.info("Initializing LLMHelper completed")

    def get_embedding_model(self) -> _EmbeddingModelProxy:
        return _EmbeddingModelProxy(self)

    def generate_embeddings(self, input: Union[str, list[int]]) -> List[float]:
        # Only pass dimensions for models that support it (text-embedding-3-*)
        # text-embedding-ada-002 does NOT support the dimensions parameter
        supports_dimensions = "text-embedding-3" in self.embedding_model.lower()
        dimensions = None
        if supports_dimensions and self.env_helper.AZURE_SEARCH_DIMENSIONS:
            dimensions = int(self.env_helper.AZURE_SEARCH_DIMENSIONS)

        kwargs = {"input": [input], "model": self.embedding_model}
        if dimensions is not None:
            kwargs["dimensions"] = dimensions

        return self.openai_client.embeddings.create(**kwargs).data[0].embedding

    def get_chat_completion(
        self, messages: list[dict], model: str | None = None, **kwargs
    ):  # pragma: no cover - unreachable while image processing is gated off
        """Chat completion is excluded (DEC-001).

        Retained as an explicit ``NotImplementedError`` so that the image
        captioning path in ``PushEmbedder.__generate_image_caption`` -- which
        is itself unreachable while ``USE_ADVANCED_IMAGE_PROCESSING=False`` --
        fails loudly if someone enables the flag prematurely.
        """
        raise NotImplementedError(
            "Chat completion is out of scope for doc-ingest-pipeline "
            "(DEC-001). Image captioning / chat paths are deferred to "
            "Phase 4 -- see spec-0002 Out of Scope."
        )
