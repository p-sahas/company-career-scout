"""
Deduplication engine using sentence-transformers.
Removes near-duplicate reviews based on cosine similarity.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-load sentence-transformers to avoid slow startup
_model = None
_model_name = "all-MiniLM-L6-v2"


def _get_model():
    """Lazy-load the sentence-transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence-transformer model: {_model_name}")
            _model = SentenceTransformer(_model_name)
            logger.info("Model loaded successfully.")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Deduplication will use fallback method."
            )
            _model = "unavailable"
    return _model


def deduplicate_results(
    results: list,
    text_key: str = "raw_text",
    similarity_threshold: float = 0.85,
) -> list:
    """
    Remove near-duplicate results based on text similarity.

    Args:
        results: List of result dicts, each containing a text field.
        text_key: Key in each dict that contains the text to compare.
        similarity_threshold: Cosine similarity threshold above which
                              items are considered duplicates (0.0–1.0).

    Returns:
        Deduplicated list of results.
    """
    if len(results) <= 1:
        return results

    model = _get_model()

    if model == "unavailable":
        return _fallback_dedup(results, text_key)

    try:
        import numpy as np

        # Extract texts
        texts = [r.get(text_key, "") for r in results]

        # Encode all texts
        embeddings = model.encode(texts, show_progress_bar=False)

        # Compute cosine similarity matrix
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        normalized = embeddings / norms
        sim_matrix = np.dot(normalized, normalized.T)

        # Greedily select non-duplicate results
        keep_indices = []
        discarded = set()

        for i in range(len(results)):
            if i in discarded:
                continue
            keep_indices.append(i)
            # Mark all similar items as duplicates
            for j in range(i + 1, len(results)):
                if j not in discarded and sim_matrix[i][j] > similarity_threshold:
                    discarded.add(j)

        deduplicated = [results[i] for i in keep_indices]
        removed_count = len(results) - len(deduplicated)
        if removed_count > 0:
            logger.info(
                f"Deduplication: removed {removed_count} duplicates "
                f"from {len(results)} results."
            )

        return deduplicated

    except Exception as e:
        logger.error(f"Deduplication error: {e}. Using fallback.")
        return _fallback_dedup(results, text_key)


def _fallback_dedup(results: list, text_key: str = "raw_text") -> list:
    """
    Fallback deduplication using simple text normalization and set matching.
    Used when sentence-transformers is not available.
    """
    seen_texts = set()
    unique_results = []

    for result in results:
        text = result.get(text_key, "")
        # Normalize: lowercase, strip whitespace, remove extra spaces
        normalized = " ".join(text.lower().split())

        # Use first 200 chars as fingerprint
        fingerprint = normalized[:200]

        if fingerprint not in seen_texts:
            seen_texts.add(fingerprint)
            unique_results.append(result)

    removed = len(results) - len(unique_results)
    if removed > 0:
        logger.info(
            f"Fallback dedup: removed {removed} duplicates from {len(results)} results."
        )

    return unique_results
