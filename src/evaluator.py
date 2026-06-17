"""
src/evaluator.py — Deterministic Grounding Evaluator
====================================================

Replaces the LLM's self-reported confidence with a mathematically defensible,
dependency-free grounding check. The core question it answers is:

    "Does every quote the model cited actually appear in the source logs?"

Scoring model (all constants are transparent and tunable below):
  * A citation found verbatim in the source (after normalization) scores 1.0.
  * A close paraphrase (>= 85% token overlap) scores PARTIAL_CREDIT (0.60) —
    grounded, but not verbatim, so it can never reach a perfect score.
  * Anything with weak overlap is treated as likely fabricated and scored
    proportionally low (overlap_ratio * 0.30), heavily penalizing it.
  * Zero citations floors the score at NO_CITATION_FLOOR (0.25): an unsourced
    article cannot be trusted regardless of how confident the model claims to be.

The final confidence is the mean grounding score across all citations, so a
single hallucinated quote drags the whole article's confidence down.

No third-party dependencies, no second LLM call — just `re` and set math.
"""

import re
from typing import List

# --- Transparent, tunable scoring constants --------------------------------
NO_CITATION_FLOOR = 0.25        # unsourced article: cannot be trusted
STRONG_OVERLAP_THRESHOLD = 0.85  # token overlap needed to count as a paraphrase
PARTIAL_CREDIT = 0.60            # score for a grounded-but-not-verbatim paraphrase
WEAK_SCALE = 0.30               # multiplier on low-overlap (likely fabricated) quotes
VERIFIED_THRESHOLD = 0.99       # a citation only counts as "verified" if verbatim

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """Lowercase and reduce text to alphanumeric tokens separated by single spaces.

    This makes matching robust to casing, punctuation, underscores
    (e.g. 'POOL_MAX' -> 'pool max') and whitespace differences, while keeping
    it strict enough that genuinely fabricated content won't match.
    """
    return _NON_ALNUM.sub(" ", str(text).lower()).strip()


def _corpus_from_logs(raw_logs: List[dict]) -> str:
    """Flatten the raw JSM logs into one searchable text blob."""
    parts = []
    for entry in raw_logs or []:
        if isinstance(entry, dict):
            if isinstance(entry.get("text"), str):
                parts.append(entry["text"])
            else:
                parts.extend(str(v) for v in entry.values() if isinstance(v, str))
        else:
            parts.append(str(entry))
    return " ".join(parts)


def _extract_quotes(citations) -> List[str]:
    """Accept an ExplainabilityTrace, a list of SourceCitation/dicts, or None."""
    if citations is None:
        return []
    # Allow passing the whole ExplainabilityTrace object.
    if hasattr(citations, "source_citations"):
        citations = citations.source_citations
    quotes = []
    for c in citations:
        if hasattr(c, "extracted_quote"):        # Pydantic SourceCitation
            quotes.append(c.extracted_quote or "")
        elif isinstance(c, dict):                # raw dict
            quotes.append(c.get("extracted_quote", "") or "")
        else:                                    # bare string
            quotes.append(str(c))
    return quotes


class DocuEvaluator:
    """Deterministic, dependency-free grounding check for generated FAQs."""

    def _grounding_score(self, norm_corpus: str, corpus_tokens: set, quote: str) -> float:
        """Return a grounding score in [0.0, 1.0] for a single quote."""
        norm_quote = _normalize(quote)
        if not norm_quote:
            return 0.0

        # Gold standard: the quote appears verbatim (normalized) in the source.
        if norm_quote in norm_corpus:
            return 1.0

        # Fallback: token-containment ratio. Order-insensitive and capped at
        # PARTIAL_CREDIT so a reshuffled paraphrase can never look "perfect".
        q_tokens = set(norm_quote.split())
        if not q_tokens:
            return 0.0
        ratio = len(q_tokens & corpus_tokens) / len(q_tokens)
        if ratio >= STRONG_OVERLAP_THRESHOLD:
            return PARTIAL_CREDIT
        return round(ratio * WEAK_SCALE, 4)

    def evaluate(self, raw_logs: List[dict], citations) -> dict:
        """Full auditable breakdown: per-citation scores + aggregate confidence."""
        norm_corpus = _normalize(_corpus_from_logs(raw_logs))
        corpus_tokens = set(norm_corpus.split())
        quotes = _extract_quotes(citations)

        if not quotes:
            return {
                "confidence_score": NO_CITATION_FLOOR,
                "total_citations": 0,
                "verified_citations": 0,
                "per_citation": [],
                "reason": "No citations supplied; applied unsourced floor.",
            }

        per_citation = []
        for q in quotes:
            score = self._grounding_score(norm_corpus, corpus_tokens, q)
            per_citation.append({
                "quote": q,
                "grounding": score,
                "verified": score >= VERIFIED_THRESHOLD,
            })

        mean_grounding = sum(p["grounding"] for p in per_citation) / len(per_citation)
        confidence = round(max(0.0, min(1.0, mean_grounding)), 4)
        verified = sum(1 for p in per_citation if p["verified"])

        return {
            "confidence_score": confidence,
            "total_citations": len(per_citation),
            "verified_citations": verified,
            "per_citation": per_citation,
            "reason": f"{verified}/{len(per_citation)} citations verified verbatim in source logs.",
        }

    def calculate_confidence(self, raw_logs: List[dict], citations) -> float:
        """Dynamic confidence in [0.0, 1.0] derived purely from source grounding."""
        return self.evaluate(raw_logs, citations)["confidence_score"]

    def validate_against_source(self, raw_logs: List[dict], citations) -> bool:
        """True only if every supplied citation is grounded verbatim in the logs."""
        report = self.evaluate(raw_logs, citations)
        return (
            report["total_citations"] > 0
            and report["verified_citations"] == report["total_citations"]
        )