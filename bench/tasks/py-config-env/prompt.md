Bug: `APP__DB__PORT=6543 python3 -m appcfg show --key db.port` still prints 5432. Nested settings can't be overridden from the environment.

Expected behaviour:
- Any variable starting with `APP__` overrides the config key at that path; `__` separates levels (`APP__DB__POOL__SIZE` is `db.pool.size`). Names are case-insensitive: config keys are lowercase.
- The value takes the type of the value it replaces: int, float, bool (`true`/`false`/`1`/`0`, any case) or string.
- A path that does not exist yet is added, as a string, creating the levels it needs.
- A value that can't be converted (for example `APP__DB__PORT=abc`) is an error: exit code 2 and a one-line message on stderr that names the variable; no traceback.
- The existing single-level form (`APP_PORT=9000`) keeps working.
