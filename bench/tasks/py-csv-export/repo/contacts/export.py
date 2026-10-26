SEPARATORS = {"csv": ",", "tsv": "\t"}


def render(rows, fields, fmt):
    sep = SEPARATORS[fmt]
    lines = [sep.join(fields)]
    for row in rows:
        lines.append(sep.join(str(row.get(f, "")) for f in fields))
    return "\n".join(lines) + "\n"
