"""Optional model providers for RAG.

KnowGSC works fully without any external service: retrieval and synthesis are
deterministic and local. When ``KNOWGSC_LLM_PROVIDER`` or
``KNOWGSC_EMBEDDING_PROVIDER`` is configured, the helpers below add optional
grounding-preserving generation or semantic similarity.

Every function fails closed: on any error it returns ``None`` and the caller
falls back to the deterministic path.
"""

import json
import os
from urllib import error, request

from django.conf import settings


def _get(name, default=""):
    return getattr(settings, name, os.environ.get(name, default)) or default


def llm_provider():
    return _get("KNOWGSC_LLM_PROVIDER").strip().lower()


def embedding_provider():
    return _get("KNOWGSC_EMBEDDING_PROVIDER").strip().lower()


def _post_json(url, payload, headers=None, timeout=25):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, ValueError, OSError):
        return None


def _chat_url(provider):
    base = _get("KNOWGSC_LLM_BASE_URL").strip().rstrip("/")
    if provider == "ollama":
        return (base or "http://localhost:11434") + "/api/chat"
    if provider in {"openai", "openai-compatible", "compatible"}:
        return (base or "https://api.openai.com/v1") + "/chat/completions"
    return ""


def generate_grounded_answer(question, passages, intro=""):
    """Ask an optional LLM to synthesize an answer strictly from passages."""

    provider = llm_provider()
    if not provider:
        return None

    url = _chat_url(provider)
    if not url:
        return None

    model = _get("KNOWGSC_LLM_MODEL", "gpt-4o-mini")
    context = "\n\n".join(
        f"[{index + 1}] {passage['source_title']} — {passage['heading']}\n{passage['text']}"
        for index, passage in enumerate(passages)
    )
    system = (
        "You are KnowGSC, a careful Google Search Console assistant. Answer only "
        "from the provided sources. Never invent a cause, a status or a fix. Keep "
        "confirmed facts separate from hypotheses, say when the sources do not "
        "answer the question, and cite sources with [1], [2] markers. Use plain "
        "language and at most 160 words."
    )
    user = (
        f"Question: {question}\n\n"
        f"Retrieved sources:\n{context}\n\n"
        "Write a short grounded answer. If the sources only partly answer the "
        "question, say what is missing."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    if provider == "ollama":
        data = _post_json(
            url,
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )
        if not data:
            return None
        return (data.get("message") or {}).get("content", "").strip() or None

    headers = {}
    api_key = _get("KNOWGSC_LLM_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = _post_json(
        url,
        {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 420,
        },
        headers=headers,
    )
    if not data:
        return None
    choices = data.get("choices") or []
    if not choices:
        return None
    return (choices[0].get("message") or {}).get("content", "").strip() or None


def embedding_model():
    return _get("KNOWGSC_EMBEDDING_MODEL", "text-embedding-3-small")


def _embedding_url(provider):
    base = _get("KNOWGSC_EMBEDDING_BASE_URL").strip().rstrip("/")
    if provider == "ollama":
        return (base or "http://localhost:11434") + "/api/embed"
    if provider in {"openai", "openai-compatible", "compatible"}:
        return (base or "https://api.openai.com/v1") + "/embeddings"
    return ""


def embed_texts(texts):
    """Return a list of vectors, or None when embeddings are unavailable."""

    provider = embedding_provider()
    if not provider or not texts:
        return None

    url = _embedding_url(provider)
    if not url:
        return None

    model = embedding_model()
    headers = {}
    api_key = _get("KNOWGSC_EMBEDDING_API_KEY") or _get("KNOWGSC_LLM_API_KEY")
    if provider != "ollama" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = _post_json(url, {"model": model, "input": texts}, headers=headers)
    if not data:
        return None

    if provider == "ollama":
        vectors = data.get("embeddings")
    else:
        ordered = sorted(data.get("data") or [], key=lambda item: item.get("index", 0))
        vectors = [item.get("embedding") for item in ordered]

    if not vectors or len(vectors) != len(texts):
        return None
    if any(not isinstance(vector, list) or not vector for vector in vectors):
        return None
    return vectors
