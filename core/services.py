"""Knowledge-topic matching kept separate from retrieval.

Topics are the editorial layer (explanation, definition, hypotheses, related
articles, investigate CTA). Retrieval answers from approved documents; a topic
adds structure when the question clearly maps to a known problem.
"""

from difflib import SequenceMatcher

from core.models import KnowledgeTopic
from core.textutils import tokenize


def _best_fuzzy(token, candidates):
    best = None
    best_ratio = 0.0
    for candidate in candidates:
        if abs(len(candidate) - len(token)) > 2:
            continue
        if len(token) > 3 and candidate[:1] != token[:1]:
            continue
        ratio = SequenceMatcher(None, token, candidate).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    if best is not None and best_ratio >= 0.8:
        return best
    return None


def match_topic(question):
    """Return the best matching KnowledgeTopic, or None when unsure."""

    query = tokenize(question)
    if not query:
        return None

    query_set = set(query)
    best_topic = None
    best_score = 0

    for topic in KnowledgeTopic.objects.all():
        terms = [topic.title, *(topic.keywords or [])]
        score = 0

        for term in terms:
            tokens = tokenize(term)
            if not tokens:
                continue
            unique = set(tokens)
            overlap = len(unique & query_set)

            if overlap == len(unique):
                score += 3 * overlap
            elif overlap:
                score += overlap
            elif len(unique) == 1:
                # A single-token term may match a misspelling in the question.
                (token,) = unique
                if any(
                    _best_fuzzy(query_token, {token})
                    for query_token in query_set
                    if query_token != token
                ):
                    score += 3

        if score > best_score:
            best_topic, best_score = topic, score

    return best_topic if best_score >= 3 else None
