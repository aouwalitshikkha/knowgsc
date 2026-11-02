"""Small, dependency-free text helpers shared by retrieval and topic matching."""

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "about", "an", "and", "any", "are", "as", "at", "be", "been", "but",
    "by", "can", "could", "did", "do", "does", "for", "from", "had", "has",
    "have", "how", "i", "if", "in", "into", "is", "it", "its", "just", "me",
    "my", "no", "not", "of", "on", "or", "our", "out", "page", "pages",
    "problem", "problems", "should", "site", "sites", "so", "some", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "to", "was", "we", "website", "were", "what", "when", "where", "which",
    "who", "why", "will", "with", "would", "you", "your",
}


def stem(token):
    """Very light stemming so 'indexed', 'indexing' and 'indexes' align."""

    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith(("ss", "us", "is")):
        return token
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("es") and len(token) > 4 and token[-3] in "sxzho":
        return token[:-2]
    if token.endswith("s"):
        return token[:-1]
    return token


def tokenize(text):
    """Return normalized, stopword-free, lightly stemmed tokens."""

    return [
        stem(token)
        for token in TOKEN_RE.findall((text or "").lower())
        if token not in STOPWORDS
    ]


def unique_tokens(text):
    return list(dict.fromkeys(tokenize(text)))
