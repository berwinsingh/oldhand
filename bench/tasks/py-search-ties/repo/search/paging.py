def page(hits, number, per_page):
    start = (number - 1) * per_page
    return hits[start:start + per_page]
