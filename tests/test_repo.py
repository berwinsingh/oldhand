"""Repository checks for the Oldhand skill pack. Stdlib only, Python 3.8+."""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, "skills")

CONDUCTOR = "oldhand"
SKILLS = [
    "oldhand", "oldhand-contract", "oldhand-trace", "oldhand-rca", "oldhand-research", "oldhand-plan",
    "oldhand-build", "oldhand-review", "oldhand-qa", "oldhand-ship", "oldhand-learn",
]
CHAIN = "contract -> trace -> rca -> research -> plan -> build -> review -> qa -> ship -> learn"
ALLOWED_KEYS = {"name", "description", "license", "metadata"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BODY_LIMIT = {CONDUCTOR: 220}
DEFAULT_BODY_LIMIT = 160

# The one file allowed to name model versions, relative to skills/.
VERSIONS_ALLOWED_IN = os.path.join("oldhand", "references", "orchestration.md")
VERSIONED_MODEL = [
    re.compile(r"\bgpt-?\d", re.I),  # gpt-6, GPT-6.1, gpt5
    re.compile(r"\bclaude-(?:[a-z]+-)?\d", re.I),  # claude-opus-5, claude-3-haiku
    re.compile(r"\bgemini[ -]\d", re.I),  # gemini-3, Gemini 2.5
    # a digit right after a family name: Opus 5.5, sonnet-4-5, Haiku 4, Sol 6
    re.compile(r"\b(?:Fable|Opus|Sonnet|Haiku|Sol|Terra|Luna|Astra|Flash|Composer)[ -]?v?\d", re.I),
]

SCRIPTS = {
    "ledger.py": os.path.join(SKILLS_DIR, "oldhand", "scripts", "ledger.py"),
    "qa.py": os.path.join(SKILLS_DIR, "oldhand-qa", "scripts", "qa.py"),
    "mutate.py": os.path.join(SKILLS_DIR, "oldhand-build", "scripts", "mutate.py"),
}
# The short names the SKILL.md files define for the scripts.
ALIASES = {"LEDGER": "ledger.py", "QA": "qa.py", "MUTATE": "mutate.py"}

AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MANIFESTS = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "plugin.json",
    "gemini-extension.json",
]

EM = chr(0x2014)  # built in code so this file does not trip its own check
TEXT_EXT = (".md", ".py", ".json", ".yaml", ".yml", ".txt", ".sh")


# ---------- a small frontmatter parser (no PyYAML) ----------

def split_frontmatter(text):
    """Return (frontmatter lines, body) or (None, text) when there is no frontmatter."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except ValueError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def fold(block, style):
    """YAML block scalar: '>' folds lines into spaces (blank line = newline), '|' keeps newlines."""
    texts = [b.strip() for b in block]
    while texts and not texts[-1]:
        texts.pop()
    if style.startswith("|"):
        out = "\n".join(texts)
    else:
        paragraphs, current = [], []
        for t in texts:
            if t:
                current.append(t)
            else:
                paragraphs.append(" ".join(current))
                current = []
        paragraphs.append(" ".join(current))
        out = "\n".join(paragraphs)
    return out if style.endswith("-") else out + "\n"


def parse_frontmatter(lines):
    """Parse `key: value`, block scalars (>-, >, |-, |), plain multi-line scalars and one-level maps."""
    data = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0] in " \t":
            raise ValueError("unexpected indented line: %r" % line)
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError("not a `key: value` line: %r" % line)
        key, value = key.strip(), value.strip()
        i += 1
        block = []
        while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
            block.append(lines[i])
            i += 1
        if key in data:
            raise ValueError("duplicate key: %s" % key)
        if value in (">", ">-", "|", "|-"):
            data[key] = fold(block, value)
        elif value == "" and any(b.strip() for b in block):
            mapping = {}
            for b in block:
                if not b.strip():
                    continue
                k, s, v = b.strip().partition(":")
                if not s or not v.strip():
                    raise ValueError("%s: only a one-level `key: value` map is supported, got %r" % (key, b))
                mapping[k.strip()] = unquote(v)
            data[key] = mapping
        else:
            rest = [b.strip() for b in block if b.strip()]
            data[key] = unquote(" ".join([value] + rest))
    return data


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_skill(name):
    """Return (text, frontmatter dict, body) or raise AssertionError with a clear message."""
    path = os.path.join(SKILLS_DIR, name, "SKILL.md")
    if not os.path.isfile(path):
        raise AssertionError("skills/%s/SKILL.md is missing" % name)
    text = read(path)
    lines, body = split_frontmatter(text)
    if lines is None:
        raise AssertionError("skills/%s/SKILL.md has no `---` frontmatter block at the top" % name)
    try:
        fm = parse_frontmatter(lines)
    except ValueError as e:
        raise AssertionError("skills/%s/SKILL.md frontmatter does not parse: %s" % (name, e))
    return text, fm, body


def code_text(markdown):
    """Fenced code blocks and inline code spans, where CLI usage is written."""
    fences = re.findall(r"```[^\n]*\n(.*?)```", markdown, re.S)
    rest = re.sub(r"```.*?```", "", markdown, flags=re.S)
    return fences + re.findall(r"`([^`\n]+)`", rest)


def walk_files(base, exts=TEXT_EXT):
    for d, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in (".git", "__pycache__", "node_modules")]
        for f in files:
            if f.endswith(exts):
                yield os.path.join(d, f)


def rel(path):
    return os.path.relpath(path, ROOT)


# ---------- tests ----------

class SkillPack(unittest.TestCase):
    def test_exactly_the_eleven_skill_folders(self):
        found = sorted(d for d in os.listdir(SKILLS_DIR)
                       if os.path.isdir(os.path.join(SKILLS_DIR, d)) and not d.startswith((".", "__")))
        self.assertEqual(found, sorted(SKILLS),
                         "skills/ must hold exactly these folders: %s" % ", ".join(SKILLS))

    def test_frontmatter(self):
        for s in SKILLS:
            with self.subTest(skill=s):
                _, fm, _ = load_skill(s)
                extra = set(fm) - ALLOWED_KEYS
                self.assertFalse(extra, "%s: frontmatter keys not allowed: %s (allowed: %s)"
                                 % (s, sorted(extra), sorted(ALLOWED_KEYS)))
                self.assertEqual(fm.get("name"), s, "%s: frontmatter name must equal the folder name" % s)
                self.assertRegex(s, NAME_RE, "%s: name must be lowercase words joined by single hyphens" % s)
                desc = fm.get("description", "")
                self.assertIsInstance(desc, str, "%s: description must be a string" % s)
                self.assertTrue(200 <= len(desc) <= 1024,
                                "%s: description is %d chars after folding; must be 200..1024" % (s, len(desc)))
                self.assertNotRegex(desc, r"[<>]", "%s: no angle brackets in a description; "
                                    "skill uploads reject anything that looks like an XML tag" % s)
                self.assertEqual(fm.get("license"), "MIT", "%s: frontmatter needs `license: MIT`" % s)
                if s == CONDUCTOR:
                    meta = fm.get("metadata")
                    self.assertIsInstance(meta, dict, "%s: needs a `metadata:` map" % s)
                    for k in ("version", "homepage"):
                        self.assertTrue(meta.get(k), "%s: metadata.%s is missing" % (s, k))
                else:
                    self.assertNotIn("metadata", fm, "%s: only the conductor carries metadata" % s)

    def test_body_line_limits(self):
        for s in SKILLS:
            with self.subTest(skill=s):
                _, _, body = load_skill(s)
                n = len(body.strip("\n").splitlines())
                limit = BODY_LIMIT.get(s, DEFAULT_BODY_LIMIT)
                self.assertLessEqual(n, limit, "%s: body is %d lines; limit is %d" % (s, n, limit))

    def test_every_skill_carries_the_chain_line(self):
        for s in SKILLS:
            with self.subTest(skill=s):
                text, _, _ = load_skill(s)
                self.assertIn(CHAIN, text, "%s: SKILL.md must contain the chain line: %s" % (s, CHAIN))

    def test_no_versioned_model_names(self):
        hits = []
        for path in list(walk_files(SKILLS_DIR, (".md",))) + [os.path.join(ROOT, "README.md")]:
            if os.path.relpath(path, SKILLS_DIR) == VERSIONS_ALLOWED_IN:
                continue
            for n, line in enumerate(read(path).splitlines(), 1):
                for rx in VERSIONED_MODEL:
                    m = rx.search(line)
                    if m:
                        hits.append("%s:%d: %r" % (rel(path), n, m.group(0)))
        self.assertEqual(hits, [], "versioned model names belong only in skills/%s; found:\n  %s"
                         % (VERSIONS_ALLOWED_IN, "\n  ".join(hits)))

    def test_one_live_run_budget_everywhere(self):
        budget = ("one per affected case, estimated first, no batches; more needs the user's yes to the count "
                  "and the estimate")
        for p in ("oldhand/SKILL.md", "oldhand-contract/SKILL.md", "oldhand-plan/SKILL.md", "oldhand-qa/SKILL.md",
                  VERSIONS_ALLOWED_IN):
            with self.subTest(file=p):
                self.assertIn(budget, " ".join(read(os.path.join(SKILLS_DIR, p)).split()),
                              "skills/%s must state the live-run budget in exactly these words: %s" % (p, budget))

    def test_skill_dir_paths_resolve(self):
        for s in SKILLS:
            with self.subTest(skill=s):
                text, _, _ = load_skill(s)
                missing = []
                for p in re.findall(r"\$\{CLAUDE_SKILL_DIR\}/([\w.\-/]+)", text):
                    p = p.rstrip(".")
                    if not os.path.exists(os.path.normpath(os.path.join(SKILLS_DIR, s, p))):
                        missing.append("${CLAUDE_SKILL_DIR}/" + p)
                self.assertEqual(missing, [], "%s: these paths do not exist relative to skills/%s/" % (s, s))

    def test_cli_subcommands_and_flags_exist(self):
        subs, flags = {}, {}
        for script, path in SCRIPTS.items():
            if not os.path.isfile(path):
                self.fail("%s is missing" % rel(path))
            src = read(path)
            subs[script] = set(re.findall(r"add_parser\(\s*[\"']([\w-]+)[\"']", src))
            flags[script] = set(re.findall(r"add_argument\(\s*[\"'](--[\w-]+)[\"']", src))
        names = r"ledger\.py|qa\.py|mutate\.py|LEDGER|QA|MUTATE"
        for s in SKILLS:
            with self.subTest(skill=s):
                text, _, _ = load_skill(s)
                unknown = []
                for chunk in code_text(text):
                    chunk = re.sub(r"(--[\w-]+)\s+\"[^\"]*\"", r"\1", chunk)  # quoted values are free text
                    used ={ALIASES.get(n, n) for n in re.findall(r"\b(%s)\b" % names, chunk)}
                    for name, sub in re.findall(r"\b(ledger\.py|qa\.py|LEDGER|QA)[\"']?\s+([a-z][a-z-]*)\b", chunk):
                        script = ALIASES.get(name, name)
                        if sub not in subs[script]:
                            unknown.append("%s %s" % (script, sub))
                    unknown += ["ledger.py finding " + x for x in re.findall(
                        r"\b(?:ledger\.py[\"']?|LEDGER)\s+finding\s+([a-z]+)\b", chunk) if x not in subs["ledger.py"]]
                    allowed = set().union(*(flags[x] for x in used)) if used else None
                    if allowed is not None and not re.search(r"\b(git|gh|curl)\b", chunk):
                        unknown += ["flag " + f for f in re.findall(r"(?<![\w-])(--[a-z][\w-]*)", chunk)
                                    if f not in allowed]
                self.assertEqual(sorted(set(unknown)), [],
                                 "%s: subcommands or flags the scripts do not define" % s)


class Manifests(unittest.TestCase):
    def load(self, relpath):
        path = os.path.join(ROOT, relpath)
        if not os.path.isfile(path):
            self.fail("%s is missing" % relpath)
        try:
            return json.loads(read(path))
        except ValueError as e:
            self.fail("%s is not valid JSON: %s" % (relpath, e))

    def test_all_parse(self):
        for m in MANIFESTS:
            with self.subTest(manifest=m):
                self.load(m)

    def test_plugin_names(self):
        names = {}
        for m in MANIFESTS:
            data = self.load(m)
            names[m] = data.get("name")
            for i, entry in enumerate(data.get("plugins", [])):
                names["%s plugins[%d]" % (m, i)] = entry.get("name")
        wrong = {k: v for k, v in names.items() if v != "oldhand"}
        self.assertEqual(wrong, {}, "every plugin name must be \"oldhand\"")

    def test_versions_match(self):
        versions = {m: self.load(m).get("version")
                    for m in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "gemini-extension.json")}
        _, fm, _ = load_skill(CONDUCTOR)
        meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
        versions["skills/oldhand/SKILL.md metadata.version"] = meta.get("version")
        self.assertEqual(len(set(versions.values())), 1, "versions differ: %s" % versions)
        self.assertTrue(all(versions.values()), "a version is missing: %s" % versions)

    def test_root_plugin_json_has_exactly_three_keys(self):
        data = self.load("plugin.json")
        self.assertEqual(sorted(data), sorted(["$schema", "name", "description"]),
                         "plugin.json (Agent Plugins 1.0) must hold only $schema, name and description")
        self.assertEqual(data["$schema"], AGENT_PLUGINS_SCHEMA)
        self.assertLessEqual(len(data["description"]), 1024)

    def test_codex_paths_exist(self):
        data = self.load(".codex-plugin/plugin.json")
        paths = [data.get("skills", "")] + [data.get("interface", {}).get(k, "") for k in ("logo", "composerIcon")]
        for p in paths:
            with self.subTest(path=p):
                self.assertTrue(p and os.path.exists(os.path.join(ROOT, p)),
                                ".codex-plugin/plugin.json points at a missing path: %r" % p)


class Hygiene(unittest.TestCase):
    def files(self, include_readme):
        out = list(walk_files(SKILLS_DIR)) + [os.path.join(ROOT, m) for m in MANIFESTS]
        if include_readme:
            out.append(os.path.join(ROOT, "README.md"))
        return [p for p in out if os.path.isfile(p)]

    def test_no_machine_paths(self):
        bad = [rel(p) for p in self.files(False) if "/Users/" in read(p)]
        self.assertEqual(bad, [], "machine-specific /Users/ paths found")

    def test_no_em_dashes(self):
        bad = [rel(p) for p in self.files(True) if EM in read(p)]
        self.assertEqual(bad, [], "em dash (U+2014) found; use a colon, comma or full stop")


if __name__ == "__main__":
    unittest.main()
