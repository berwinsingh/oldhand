Bug: `GET /items?tag=red&tag=large` returns red items of every size, and `?tag=red` misses the items tagged `Red` or `RED`.

Expected behaviour:
- Repeated `tag` parameters mean AND: return only the items that have every one of the given tags.
- Tags match case-insensitively (`red`, `Red` and `RED` are the same tag).
- A tag that no item has returns an empty list with status 200.
- `/items` with no tag, `/items/:id`, and the 404 for a missing id keep working exactly as now.
