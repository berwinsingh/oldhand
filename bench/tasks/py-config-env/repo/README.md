# appcfg

Loads `config.json` and lets environment variables override it.

    python3 -m appcfg show            # key = value lines
    python3 -m appcfg show --json     # the merged config as JSON
    APP_PORT=9000 python3 -m appcfg show --key port

Run the tests with `python3 -m unittest discover -s tests`.
