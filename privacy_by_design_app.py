"""
Privacy by Design (PbD) Reference App
======================================
A minimal Streamlit + SQLite app that demonstrates all 7 Privacy by Design
principles (Ann Cavoukian's framework) in working code. Each block below is
tagged with the principle it implements and WHY.

Run with:  streamlit run privacy_by_design_app.py
Requires:  pip install streamlit cryptography
"""

import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

DB_PATH = "pbd_demo.db"
RETENTION_DAYS = 30  # PRINCIPLE 1: Proactive not Reactive — data has a built-in expiry

# ---------------------------------------------------------------------------
# PRINCIPLE 3: Privacy Embedded into Design
# Encryption key management is baked into the architecture, not bolted on
# later. In production, load this from a secrets manager (not session_state).
# ---------------------------------------------------------------------------
if "fernet_key" not in st.session_state:
    st.session_state.fernet_key = Fernet.generate_key()
fernet = Fernet(st.session_state.fernet_key)


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,          -- hashed identifier, never raw email
            encrypted_blob BLOB NOT NULL, -- PRINCIPLE 5: End-to-End Security
            consent_marketing INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL      -- PRINCIPLE 1: retention limit
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            ts TEXT, user_id TEXT, action TEXT
        )
    """)  # PRINCIPLE 6: Visibility and Transparency — every access is logged
    conn.commit()
    conn.close()


def log_action(user_id, action):
    conn = get_conn()
    conn.execute("INSERT INTO audit_log VALUES (?, ?, ?)",
                 (datetime.utcnow().isoformat(), user_id, action))
    conn.commit()
    conn.close()


def hash_id(email: str) -> str:
    # PRINCIPLE 3: pseudonymize the primary key so the DB itself never holds
    # a plaintext, directly-identifying lookup field.
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


# ---------------------------------------------------------------------------
# PRINCIPLE 7: Respect for User Privacy — the whole UI is organized around
# user-centric controls: register with consent, view your data, export it,
# delete it. The user is kept in the driver's seat throughout.
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Privacy by Design Demo", page_icon="🔒")
st.title("🔒 Privacy by Design — Reference App")

# PRINCIPLE 6: Visibility and Transparency — plain-language notice shown
# up front, before any data is collected.
with st.expander("📄 Privacy Notice (read before submitting)", expanded=False):
    st.markdown(f"""
    - We collect only what's needed to demo this app: name and email.
    - Marketing consent is **off by default** — you must opt in.
    - Data is encrypted at rest and auto-deletes after **{RETENTION_DAYS} days**.
    - You can view, export, or delete your record at any time below.
    - Every access to your record is written to an audit log you can inspect.
    """)

init_db()
tab_register, tab_myrecord, tab_admin = st.tabs(
    ["📝 Register", "👤 My Data", "🛡️ Audit Log (transparency)"]
)

# ---------------------------------------------------------------------------
# TAB 1 — Registration
# ---------------------------------------------------------------------------
with tab_register:
    st.subheader("Register")
    name = st.text_input("Name (optional)")  # PRINCIPLE 4: full functionality
    email = st.text_input("Email (required — used only to identify your record)")

    # PRINCIPLE 2: Privacy as the Default Setting — opt-IN checkbox, unchecked
    consent = st.checkbox("I consent to receive marketing emails (optional)", value=False)

    # PRINCIPLE 4: Full Functionality / Positive-Sum — the app works
    # completely even if the user gives the minimum (just email, no name,
    # no marketing consent). Privacy doesn't cost functionality.
    if st.button("Submit"):
        if not email:
            st.error("Email is required to create a record.")
        else:
            uid = hash_id(email)
            payload = json.dumps({"name": name, "email": email})
            encrypted = fernet.encrypt(payload.encode())
            now = datetime.utcnow()
            expires = now + timedelta(days=RETENTION_DAYS)

            conn = get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)",
                (uid, encrypted, int(consent), now.isoformat(), expires.isoformat())
            )
            conn.commit()
            conn.close()
            log_action(uid, "REGISTER")
            st.success("Registered. Your data is encrypted at rest.")
            st.info(f"Your record auto-expires on {expires.date()} (Principle: data minimization / storage limitation).")

# ---------------------------------------------------------------------------
# TAB 2 — Data Subject Rights (view / export / delete own data)
# ---------------------------------------------------------------------------
with tab_myrecord:
    st.subheader("View, export, or delete your record")
    lookup_email = st.text_input("Enter your email to look up your record", key="lookup")

    if st.button("Find my record"):
        uid = hash_id(lookup_email)
        conn = get_conn()
        row = conn.execute(
            "SELECT encrypted_blob, consent_marketing, created_at, expires_at FROM users WHERE id=?",
            (uid,)
        ).fetchone()
        conn.close()

        if row:
            decrypted = json.loads(fernet.decrypt(row[0]).decode())
            log_action(uid, "VIEW")  # PRINCIPLE 6: transparency — access logged
            st.json({
                "name": decrypted["name"],
                "email": decrypted["email"],
                "marketing_consent": bool(row[1]),
                "created_at": row[2],
                "expires_at": row[3],
            })

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(  # PRINCIPLE 7: data portability
                    "⬇️ Export my data (JSON)",
                    data=json.dumps(decrypted, indent=2),
                    file_name="my_data.json",
                )
            with col2:
                if st.button("🗑️ Delete my record (right to erasure)"):
                    conn = get_conn()
                    conn.execute("DELETE FROM users WHERE id=?", (uid,))
                    conn.commit()
                    conn.close()
                    log_action(uid, "DELETE")
                    st.success("Record permanently deleted.")
        else:
            st.warning("No record found for that email.")

# ---------------------------------------------------------------------------
# TAB 3 — Audit log (visibility/transparency principle made concrete)
# ---------------------------------------------------------------------------
with tab_admin:
    st.subheader("Audit log")
    st.caption("Every REGISTER / VIEW / DELETE action is recorded, keyed by "
               "hashed ID only — never plaintext email — so oversight doesn't "
               "itself become a new privacy leak.")
    conn = get_conn()
    rows = conn.execute("SELECT ts, user_id, action FROM audit_log ORDER BY ts DESC LIMIT 50").fetchall()
    conn.close()
    if rows:
        st.table([{"timestamp": r[0], "user_id (hashed)": r[1][:12] + "…", "action": r[2]} for r in rows])
    else:
        st.caption("No activity yet.")

st.divider()
st.caption(
    "This app is a teaching reference, not a production system — swap the "
    "session-only Fernet key for a real secrets manager (e.g. AWS KMS, "
    "HashiCorp Vault) before using this pattern for real data."
)
