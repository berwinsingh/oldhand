import re

WORD = re.compile(r"[a-z0-9]+")


def words(text):
    return WORD.findall(text.lower())


def build(articles):
    """word -> set of article ids that contain it (title or body)."""
    idx = {}
    for a in articles:
        for w in set(words(a["title"]) + words(a["body"])):
            idx.setdefault(w, set()).add(a["id"])
    return idx
