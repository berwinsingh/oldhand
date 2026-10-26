import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from appcfg.__main__ import main

BASE = {"name": "shop", "port": 8080, "debug": False, "db": {"host": "localhost", "port": 5432}}


class ConfigTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            json.dump(BASE, fh)

    def show(self, environ, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["--config", self.path, "show"] + list(args), environ=environ)
        return buf.getvalue()

    def test_no_env_shows_the_file(self):
        self.assertEqual(json.loads(self.show({}, "--json")), BASE)

    def test_top_level_override_keeps_the_type(self):
        self.assertEqual(self.show({"APP_PORT": "9000"}, "--key", "port").strip(), "9000")


if __name__ == "__main__":
    unittest.main()
