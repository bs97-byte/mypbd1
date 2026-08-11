# mypbd1

Run it with `pip install streamlit cryptography` then `streamlit run privacy_by_design_app.py`.

Where each of the 7 principles lives in the code:

1. **Proactive not Reactive** — `RETENTION_DAYS` builds an auto-expiry into every record at creation time, before any breach or complaint could happen.
2. **Privacy as the Default Setting** — the marketing consent checkbox defaults to unchecked (opt-in only); only email is required.
3. **Privacy Embedded into Design** — Fernet encryption and `hash_id()` pseudonymization aren't add-ons, they're structural: the DB schema itself only ever stores hashed IDs and encrypted blobs.
4. **Full Functionality (Positive-Sum)** — the app works completely with just an email; name and marketing consent are optional, so privacy doesn't trade off against usability.
5. **End-to-End Security** — data is encrypted before it touches disk (`encrypted_blob`) and decrypted only transiently in memory when the owner requests it.
6. **Visibility and Transparency** — the Privacy Notice expander, and the `audit_log` table + "Audit Log" tab, make data practices inspectable rather than hidden.
7. **Respect for User Privacy** — the "My Data" tab gives the user view, export (portability), and delete (erasure) controls over their own record — the whole UI is organized around the data subject, not the admin.

Two things worth flagging as demo-only shortcuts: the encryption key lives in `st.session_state` (would need a real secrets manager in production), and there's no auth on the lookup form (anyone who knows an email can pull that record) — I'd add login/verification before this touched real data.
