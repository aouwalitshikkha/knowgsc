"""Local retrieval-augmented generation for KnowGSC.

Design goals from the product blueprint (section 5):

* retrieval over reviewed, approved knowledge only;
* deterministic answers by default - no external model required;
* every answer cites the documents it came from;
* hypotheses stay labelled as hypotheses;
* unknown questions are recorded as knowledge gaps.

The retriever is a small BM25 index over document chunks. It tolerates
misspellings through the reviewed ``SearchTerm`` table and fuzzy vocabulary
matching. Optional embeddings and an optional LLM are layered on top when
configured, and both fail closed.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher

from django.db.models import Count, Max

from core import rag_providers
from core.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeGap,
    QuestionLog,
    SearchTerm,
)
from core.services import match_topic
from core.textutils import tokenize

HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
NUMBERED_RE = re.compile(r"^\d+[.)]\s+")

ACTION_HEADINGS = (
    ("How to check", ("how to check", "how to investigate", "how to diagnose")),
    ("How to fix", ("how to fix", "what to do", "recommended actions")),
    ("How to verify", ("how to verify", "verify results", "verification")),
)

# Editorial alignment between a topic and the document that answers it best.
TOPIC_DOCUMENT_BOOST = {
    "discovered-not-indexed": {"discovered-not-indexed"},
    "crawled-not-indexed": {"crawled-not-indexed"},
    "blocked-by-robots": {"robots-txt-blocked"},
    "canonical-issues": {"canonicalization-duplicates"},
    "server-errors": {"server-errors-5xx"},
}


# ---------------------------------------------------------------------------
# Chunking + indexing
# ---------------------------------------------------------------------------


def split_sections(body):
    """Split a document body on ``## Heading`` markers."""

    body = (body or "").strip()
    if not body:
        return []

    matches = list(HEADING_RE.finditer(body))
    if not matches:
        return [("Overview", body)]

    sections = []
    preface = body[: matches[0].start()].strip()
    if preface:
        sections.append(("Overview", preface))

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        if content:
            sections.append((match.group(1).strip(), content))

    return sections


def reindex_document(document):
    """Rebuild chunks for one document. Returns the number of chunks."""

    document.chunks.all().delete()
    sections = split_sections(document.body)
    if not sections:
        return 0

    vectors = None
    if rag_providers.embedding_provider():
        inputs = [
            f"{document.title}\n{heading}\n{content}"
            for heading, content in sections
        ]
        vectors = rag_providers.embed_texts(inputs)

    for order, (heading, content) in enumerate(sections):
        chunk = KnowledgeChunk(
            document=document,
            order=order,
            heading=heading,
            content=content,
        )
        if vectors and order < len(vectors):
            chunk.embedding = vectors[order]
            chunk.embedding_model = rag_providers.embedding_model()
        chunk.save()

    return len(sections)


def reindex_all():
    """Re-chunk every published, approved document."""

    documents = KnowledgeDocument.objects.filter(
        is_published=True,
        review_status=KnowledgeDocument.ReviewStatus.APPROVED,
    )
    total = 0
    for document in documents:
        total += reindex_document(document)
    _INDEX["fingerprint"] = None
    return total


# ---------------------------------------------------------------------------
# BM25 index
# ---------------------------------------------------------------------------


@dataclass
class Entry:
    chunk: KnowledgeChunk
    tf: Counter
    length: int


@dataclass
class ScoredChunk:
    score: float
    coverage: float
    entry: Entry


_INDEX = {"fingerprint": None, "data": None}
_TERMS = {"fingerprint": None, "map": None}


def _index_fingerprint():
    aggregate = KnowledgeChunk.objects.aggregate(count=Count("id"), latest=Max("updated_at"))
    latest = aggregate["latest"]
    return (aggregate["count"], latest.isoformat() if latest else None)


def _build_index():
    chunks = list(
        KnowledgeChunk.objects.select_related("document").filter(
            document__is_published=True,
            document__review_status=KnowledgeDocument.ReviewStatus.APPROVED,
        )
    )

    entries = []
    document_frequency = Counter()

    for chunk in chunks:
        # Titles and headings are repeated to give them a field boost.
        text = " ".join(
            [
                chunk.document.title,
                chunk.document.title,
                chunk.heading,
                chunk.heading,
                chunk.document.summary,
                chunk.content,
            ]
        )
        tokens = tokenize(text)
        term_frequency = Counter(tokens)
        document_frequency.update(term_frequency.keys())
        entries.append(Entry(chunk=chunk, tf=term_frequency, length=len(tokens)))

    total = len(entries)
    average_length = sum(entry.length for entry in entries) / total if total else 0.0
    inverse_frequency = {
        term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
        for term, frequency in document_frequency.items()
    }

    return {
        "entries": entries,
        "idf": inverse_frequency,
        "avgdl": average_length or 1.0,
        "vocab": set(document_frequency),
    }


def get_index():
    fingerprint = _index_fingerprint()
    if _INDEX["fingerprint"] != fingerprint:
        _INDEX["data"] = _build_index()
        _INDEX["fingerprint"] = fingerprint
    return _INDEX["data"]


def _search_term_map():
    terms = list(SearchTerm.objects.all())
    fingerprint = (len(terms), tuple(sorted(term.pk for term in terms)))
    if _TERMS["fingerprint"] == fingerprint:
        return _TERMS["map"]

    mapping = {}
    for term in terms:
        canonical = set(tokenize(term.term))
        variants = set(canonical)
        for variant in term.misspellings or []:
            variants.update(tokenize(variant))
        synonyms = set()
        for synonym in term.synonyms or []:
            synonyms.update(tokenize(synonym))

        expansion = canonical | synonyms
        for variant in variants:
            mapping.setdefault(variant, set()).update(expansion)
        for synonym in synonyms:
            mapping.setdefault(synonym, set()).update(expansion)

    _TERMS["fingerprint"] = fingerprint
    _TERMS["map"] = mapping
    return mapping


# ---------------------------------------------------------------------------
# Query expansion + retrieval
# ---------------------------------------------------------------------------


def expand_query(query_tokens, vocabulary):
    """Return ``{token: weight}`` with synonyms and fuzzy typo expansion."""

    weights = Counter({token: 1.0 for token in query_tokens})
    term_map = _search_term_map()

    for token in set(query_tokens):
        for expanded in term_map.get(token, ()):
            weights[expanded] = max(weights[expanded], 0.9)

    for token in set(query_tokens):
        if token in vocabulary or len(token) < 4:
            continue
        best = None
        best_ratio = 0.0
        for candidate in vocabulary:
            if abs(len(candidate) - len(token)) > 2:
                continue
            if candidate[:1] != token[:1]:
                continue
            ratio = SequenceMatcher(None, token, candidate).ratio()
            if ratio > best_ratio:
                best, best_ratio = candidate, ratio
        if best is not None and best_ratio >= 0.85:
            weights[best] = max(weights[best], 0.8)

    return weights


def _cosine(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _embedding_scores(question, entries):
    if not rag_providers.embedding_provider():
        return {}
    vectors = rag_providers.embed_texts([question])
    if not vectors:
        return {}
    question_vector = vectors[0]
    scores = {}
    for entry in entries:
        if entry.chunk.embedding:
            scores[entry.chunk.pk] = _cosine(question_vector, entry.chunk.embedding)
    return scores


def retrieve(question, limit=8, boost_slugs=()):
    """Return ``(scored_chunks, query_weights)`` ordered by relevance."""

    index = get_index()
    query_tokens = tokenize(question)
    if not query_tokens or not index["entries"]:
        return [], {}

    weights = expand_query(query_tokens, index["vocab"])
    query_set = set(query_tokens)
    average_length = index["avgdl"]
    k1, b = 1.5, 0.75
    boost_slugs = set(boost_slugs)

    semantic = _embedding_scores(question, index["entries"])
    phrase = question.lower().strip(" ?.!")

    scored = []
    for entry in index["entries"]:
        length = entry.length or 1
        score = 0.0

        for term, weight in weights.items():
            frequency = entry.tf.get(term, 0)
            if not frequency:
                continue
            inverse = index["idf"].get(term, 0.0)
            denominator = frequency + k1 * (1 - b + b * length / average_length)
            score += weight * inverse * (frequency * (k1 + 1)) / denominator

        if semantic.get(entry.chunk.pk):
            score += 2.0 * max(0.0, semantic[entry.chunk.pk])

        if score <= 0:
            continue

        coverage = len(query_set & set(entry.tf)) / len(query_set)
        score *= 0.85 + 0.15 * coverage

        if phrase and phrase in entry.chunk.content.lower():
            score += 1.5

        if entry.chunk.document.slug in boost_slugs:
            score += 3.0

        slug_tokens = set(tokenize(entry.chunk.document.slug.replace("-", " ")))
        score += 1.5 * len(query_set & slug_tokens)

        scored.append(ScoredChunk(score=score, coverage=coverage, entry=entry))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit], weights


# ---------------------------------------------------------------------------
# Deterministic synthesis
# ---------------------------------------------------------------------------


def _flatten(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _sentences(text):
    flat = _flatten(text)
    if not flat:
        return []
    return [sentence.strip() for sentence in SENTENCE_RE.split(flat) if sentence.strip()]


def _excerpt(text, limit=460):
    flat = _flatten(text)
    if len(flat) <= limit:
        return flat
    cut = flat[:limit]
    boundary = cut.rfind(". ")
    if boundary > limit * 0.5:
        return cut[: boundary + 1]
    return cut.rstrip() + "…"


def _bullet_items(content):
    items = []
    for raw_line in (content or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("-", "*", "•")):
            line = line[1:].strip()
        elif NUMBERED_RE.match(line):
            line = NUMBERED_RE.sub("", line)
        else:
            continue
        if len(line) > 15:
            items.append(line)
    return items


def _action_steps(scored, minimum_score):
    groups = []
    for label, needles in ACTION_HEADINGS:
        items = []
        seen = set()
        for item in scored:
            if item.score < minimum_score:
                continue
            heading = item.entry.chunk.heading.lower()
            if not any(needle in heading for needle in needles):
                continue
            content = item.entry.chunk.content
            candidates = _bullet_items(content) or _sentences(content)
            for candidate in candidates:
                key = candidate.lower()
                if key in seen:
                    continue
                seen.add(key)
                items.append(candidate)
                if len(items) >= 6:
                    break
            if len(items) >= 6:
                break
        if items:
            groups.append({"heading": label, "items": items})
    return groups


def _key_points(scored, query_tokens, used_sentences):
    query_set = set(query_tokens)
    points = []
    seen = {sentence.lower() for sentence in used_sentences}

    for item in scored:
        for sentence in _sentences(item.entry.chunk.content):
            if len(points) >= 5:
                return points
            if len(sentence) < 45 or len(sentence) > 260:
                continue
            key = sentence.lower()
            if key in seen:
                continue
            if not (query_set & set(tokenize(sentence))):
                continue
            seen.add(key)
            points.append(sentence)

    return points


def _confidence(top_score):
    if top_score >= 7.0:
        return "high", "High confidence", "chip-ok"
    if top_score >= 3.0:
        return "medium", "Medium confidence", "chip-warn"
    return "low", "Low confidence", "chip-neutral"


def _build_answer(question, scored, topic):
    query_tokens = tokenize(question)
    top_score = scored[0].score
    usable = [item for item in scored if item.score >= max(1.2, top_score * 0.28)]

    passages = []
    per_document = Counter()
    seen = set()

    for item in usable:
        chunk = item.entry.chunk
        if per_document[chunk.document_id] >= 2:
            continue
        key = (chunk.document_id, chunk.heading)
        if key in seen:
            continue
        seen.add(key)
        per_document[chunk.document_id] += 1
        passages.append(
            {
                "heading": chunk.heading or "Overview",
                "text": _excerpt(chunk.content),
                "source_title": chunk.document.title,
                "source_url": chunk.document.url,
                "source_slug": chunk.document.slug,
                "doc_type": chunk.document.get_doc_type_display(),
                "score": round(item.score, 2),
            }
        )
        if len(passages) >= 4:
            break

    if not passages:
        return None

    intro = ""
    if topic and topic.explanation:
        intro = topic.explanation
    else:
        intro_sentences = _sentences(passages[0]["text"])
        if intro_sentences:
            intro = intro_sentences[0]
            if len(intro) < 150 and len(intro_sentences) > 1:
                intro = f"{intro} {intro_sentences[1]}"

    used = _sentences(intro)
    key_points = _key_points(usable, query_tokens, used)
    steps = _action_steps(usable, minimum_score=max(0.8, top_score * 0.2))

    sources = []
    seen_documents = set()
    for passage in passages:
        if passage["source_slug"] in seen_documents:
            continue
        seen_documents.add(passage["source_slug"])
        sources.append(
            {
                "title": passage["source_title"],
                "url": passage["source_url"],
                "doc_type": passage["doc_type"],
            }
        )

    confidence, confidence_label, confidence_class = _confidence(top_score)

    return {
        "question": question,
        "no_match": False,
        "intro": intro,
        "key_points": key_points,
        "passages": passages,
        "steps": steps,
        "sources": sources,
        "hypotheses": list(topic.causes or []) if topic else [],
        "definition": topic.definition if topic else "",
        "topic": topic,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "confidence_class": confidence_class,
        "top_score": round(top_score, 2),
        "retrieved_count": len(scored),
        "llm_text": rag_providers.generate_grounded_answer(question, passages, intro),
    }


def _no_match(question, scored, topic):
    return {
        "question": question,
        "no_match": True,
        "intro": "",
        "key_points": [],
        "passages": [],
        "steps": [],
        "sources": [],
        "hypotheses": [],
        "definition": "",
        "topic": topic,
        "confidence": "low",
        "confidence_label": "No reviewed match",
        "confidence_class": "chip-neutral",
        "top_score": round(scored[0].score, 2) if scored else 0.0,
        "retrieved_count": len(scored),
        "llm_text": None,
    }


def answer_question(question, log_gap=True, log_question=False):
    """Retrieve approved knowledge and build a grounded, cited answer."""

    question = (question or "").strip()
    if not question:
        return _no_match("", [], None)

    topic = match_topic(question)
    boost = TOPIC_DOCUMENT_BOOST.get(topic.slug, set()) if topic else set()
    scored, _weights = retrieve(question, boost_slugs=boost)

    if not scored or scored[0].score < 0.9:
        answer = _no_match(question, scored, topic)
    else:
        answer = _build_answer(question, scored, topic)
        if answer is None:
            answer = _no_match(question, scored, topic)

    if log_gap and (answer["no_match"] or answer["confidence"] == "low"):
        KnowledgeGap.objects.create(
            question=question[:500],
            matched_topic=topic,
            retrieved_count=answer["retrieved_count"],
        )

    if log_question:
        QuestionLog.objects.create(
            question=question[:500],
            matched_topic=topic,
            confidence=(
                QuestionLog.Confidence.NONE
                if answer["no_match"]
                else answer["confidence"]
            ),
            no_match=answer["no_match"],
            retrieved_count=answer["retrieved_count"],
        )

    return answer
