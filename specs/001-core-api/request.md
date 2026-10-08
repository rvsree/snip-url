# Request: Core URL shortener (S1)

Type: Greenfield, well-defined

We need a simple URL shortener service.

1. A user sends a long URL and gets back a short code (7 characters, letters and digits) and the full short URL.
2. Only http and https URLs are accepted, up to 2048 characters. Anything else is rejected with a clear error message.
3. Opening the short URL redirects the user to the original long URL (HTTP 302).
4. An unknown short code returns 404 with a clear error message.
5. Every redirect is recorded as a click with its time.
6. A user can see the stats for a short code: the original URL, when it was created, and the total click count.
7. Data must survive a restart (store it in SQLite).
8. A health endpoint confirms the service is up.

Not needed now: user accounts, custom aliases, link expiry, editing or deleting links.
