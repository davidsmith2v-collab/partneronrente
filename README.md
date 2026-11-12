# PartnerRent – Flask + SQLite starter website

A responsive, adults-only companion and conversation marketplace starter project.

## Included
- Responsive HTML templates and custom CSS
- User registration and login with Werkzeug password hashing
- SQLite database created automatically on first run
- Public companion profiles and discover filters
- Booking requests for calls and public meetups
- Member dashboard with accept/decline controls
- Profile reporting
- SEO titles, descriptions, canonical tags, JSON-LD, sitemap and robots.txt
- Basic CSRF token validation on forms

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create a virtual environment (recommended):
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Set a strong secret key before deployment:
   - PowerShell: `$env:SECRET_KEY="replace-with-a-long-random-secret"`
   - macOS/Linux: `export SECRET_KEY="replace-with-a-long-random-secret"`
6. Start: `python app.py`
7. Visit http://127.0.0.1:5000

The SQLite database `partnerrent.db` is generated automatically in this folder.

## Important before public launch
This is a working MVP foundation, not a fully production-certified marketplace. It intentionally does not collect payments or verify identity. Before launch:
- Integrate a compliant payment gateway (e.g. Razorpay/ Cashfree) using merchant credentials and server-side payment verification; never store card/UPI credentials.
- Add email/phone OTP verification, photo moderation, identity/age assurance, admin moderation dashboard, blocking, appeals and a staffed safety process.
- Add rate limiting, secure cookie settings, HTTPS, database backups, logging, monitoring and a production WSGI server.
- Replace example domain/canonical/sitemap URLs with your real domain.
- Use licensed photos and obtain consent for profile photos.
- Have Indian legal counsel review privacy, consumer, intermediary, tax, safety and platform obligations.
- Keep the service limited to lawful, consensual companionship and conversation; prohibit sexual services, coercion, trafficking, exploitation and minors.

## Database
Tables: `users`, `bookings`, `reports`. The schema is created in `app.py` by `init_db()`.
