"""Inert stub for Azure AI Vision (image vectorization).

The parent accelerator's ``azure_computer_vision_client.py`` implements
multimodal image embeddings via the Azure AI Vision Vectorize Image /
Vectorize Text APIs. ``doc-ingest-pipeline`` defers all image processing
to **Phase 4** (per the spec-0002 Out-of-Scope table and DEC entries for
the headless ingestion product). The full implementation is intentionally
not ported.

This stub keeps the import surface intact so ``AzureSearchHelper``,
``AzureSearchHandler``, and ``PushEmbedder`` -- which always *instantiate*
the client during ``__init__`` -- continue to load. Any actual call to
``vectorize_image`` / ``vectorize_text`` raises ``NotImplementedError`` and
will only be hit when ``USE_ADVANCED_IMAGE_PROCESSING=True``, which is
forced to ``False`` in this product.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)


class AzureComputerVisionClient:
    _NOT_IMPLEMENTED_MSG = (
        "Advanced image processing is out of scope for doc-ingest-pipeline "
        "Phase 1 (see spec-0002 Out of Scope and DEC-001/DEC-002/DEC-004). "
        "Set USE_ADVANCED_IMAGE_PROCESSING=False (the default) or wait for "
        "the Phase 4 image-processing spec."
    )

    def __init__(self, env_helper) -> None:  # noqa: ANN001 - upstream signature
        self.env_helper = env_helper
        logger.debug(
            "AzureComputerVisionClient stub initialized; "
            "image vectorization is deferred to Phase 4."
        )

    def vectorize_image(self, image_url: str) -> List[float]:  # pragma: no cover
        raise NotImplementedError(self._NOT_IMPLEMENTED_MSG)

    def vectorize_text(self, text: str) -> List[float]:  # pragma: no cover
        raise NotImplementedError(self._NOT_IMPLEMENTED_MSG)
