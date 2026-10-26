SEPARATORS = {"csv": ",", "tsv": "\t"}


def cell(value, sep):
    text = str(value)
    return '"%s"' % text if sep in text else text


def render(rows, fields, fmt):
    sep = SEPARATORS[fmt]
    lines = [sep.join(fields)]
    for row in rows:
        lines.append(sep.join(cell(row.get(f, ""), sep) for f in fields))
    return "\n".join(lines) + "\n"
