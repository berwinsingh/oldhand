# accounts

Sign-in for the customer portal: a small JSON API with cookie sessions, no dependencies.

    node server.js --port 3000
    POST /login    {"email", "password", "remember"}   sets the session cookie
    POST /refresh  rotates the session (the portal calls it every 15 minutes)
    POST /logout
    GET  /me       {"email", "expiresAt"} for a valid session, 401 otherwise

Users are in `data/users.json`. Run the tests with `npm test`.
