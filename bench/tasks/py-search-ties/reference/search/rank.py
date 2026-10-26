import re

from .index import words


def score(article, terms):
    """Each query word: +1 per occurrence in the body, +2 per occurrence in the title."""
    title, body = words(article["title"]), words(article["body"])
    return sum(2 * title.count(t) + body.count(t) for t in terms)


def natural(doc_id):
    """doc-2 before doc-10: digit runs compare as numbers."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", doc_id)]


def ranked(idx, articles, query):
    terms = words(query)
    candidates = set()
    for t in terms:
        candidates |= idx.get(t, set())
    scored = [(doc_id, score(articles[doc_id], terms)) for doc_id in candidates]
    scored.sort(key=lambda pair: (-pair[1], natural(pair[0])))
    return scored
