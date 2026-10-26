Bug: customers who tick "remember me" are signed out after about an hour, or as soon as they close the browser.

Expected behaviour:
- Signing in with `"remember": true` keeps the customer signed in for 30 days: the cookie has `Max-Age=2592000` and the server-side session expires 30 days after sign-in (`GET /me` reports it in `expiresAt`).
- Without "remember me", the cookie has no `Max-Age` (it ends with the browser) and the session expires after 1 hour.
- `POST /refresh` gives a new session id (the old one stops working at once) and keeps the kind of session: a remembered session stays remembered, with a fresh 30 days; a normal one gets a fresh hour.
- Every session cookie keeps `HttpOnly`, `Path=/` and `SameSite=Lax`. Logout still clears the cookie and ends the session.
