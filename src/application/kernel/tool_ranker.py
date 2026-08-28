"""
Fast In-Memory BM25 Tool Ranker & 3-Tier Tool Resolution [REQ-MCP-004].
Preserves LLM context budgets by ranking and mounting only top-K relevant tool schemas.
"""

import math
import re
from collections import Counter
from typing import Dict, List, Optional, Set

from src.domain.gateway.models import ToolDefinition


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric keywords."""
    if not text:
        return []
    return [t for t in re.split(r"[^a-zA-Z0-9_]+", text.lower()) if len(t) > 1]


class ToolRanker:
    """
    Sub-millisecond in-memory BM25 ranker for dynamic tool resolution.
    """

    @classmethod
    def rank_tools(
        cls,
        query: str,
        tools: List[ToolDefinition],
        pinned_tool_names: Optional[List[str]] = None,
        max_tools: int = 6,
    ) -> List[ToolDefinition]:
        """
        Ranks tool definitions using BM25 scoring against user query while preserving pinned tools.
        """
        if not tools or len(tools) <= max_tools:
            return list(tools)

        pinned_set: Set[str] = set(pinned_tool_names or [])
        pinned_tools = [t for t in tools if t.name in pinned_set]
        candidate_tools = [t for t in tools if t.name not in pinned_set]

        # Remaining capacity for ranked tools
        remaining_slots = max(0, max_tools - len(pinned_tools))
        if remaining_slots == 0:
            return pinned_tools[:max_tools]

        query_tokens = _tokenize(query)
        if not query_tokens:
            # Fallback when query is empty: return pinned + first N candidate tools
            return pinned_tools + candidate_tools[:remaining_slots]

        # Prepare corpus for BM25
        doc_tokens_list: List[List[str]] = []
        for t in candidate_tools:
            # Tool doc combines name (weighted 3x), description (weighted 2x), and parameter keys
            name_toks = _tokenize(t.name) * 3
            desc_toks = _tokenize(t.description) * 2
            param_toks = _tokenize(" ".join(t.parameters.get("properties", {}).keys()))
            doc_tokens_list.append(name_toks + desc_toks + param_toks)

        num_docs = len(candidate_tools)
        avg_doc_len = sum(len(d) for d in doc_tokens_list) / max(1, num_docs)

        # Calculate Document Frequency (DF) for each query token
        df: Dict[str, int] = Counter()
        for doc in doc_tokens_list:
            unique_terms = set(doc)
            for term in query_tokens:
                if term in unique_terms:
                    df[term] += 1

        # BM25 Parameters
        k1 = 1.5
        b = 0.75

        # Score each candidate tool
        scores: List[float] = []
        for idx, doc in enumerate(doc_tokens_list):
            doc_len = len(doc)
            term_counts = Counter(doc)
            score = 0.0

            for q_term in query_tokens:
                if q_term not in term_counts:
                    continue

                tf = term_counts[q_term]
                term_df = df[q_term]
                idf = math.log((num_docs - term_df + 0.5) / (term_df + 0.5) + 1.0)
                numerator = tf * (k1 + 1.0)
                denominator = tf + k1 * (1.0 - b + b * (doc_len / avg_doc_len))
                score += idf * (numerator / denominator)

            scores.append(score)

        # Sort candidate tools by score descending (stable sort preserving original order for ties)
        ranked_candidates = [
            tool
            for _, tool in sorted(
                enumerate(candidate_tools),
                key=lambda item: (-scores[item[0]], item[0]),
            )
        ]

        return pinned_tools + ranked_candidates[:remaining_slots]
