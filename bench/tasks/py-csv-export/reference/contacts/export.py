import csv
import io

SEPARATORS = {"csv": ",", "tsv": "\t"}
FORMULA_START = ("=", "+", "-", "@")


def safe(value):
    text = str(value)
    return "'" + text if text.startswith(FORMULA_START) else text


def render(rows, fields, fmt):
    if fmt == "tsv":
        lines = ["\t".join(fields)]
        for row in rows:
            lines.append("\t".join(str(row.get(f, "")) for f in fields))
        return "\n".join(lines) + "\n"
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(fields)
    for row in rows:
        writer.writerow([safe(row.get(f, "")) for f in fields])
    return buf.getvalue()
