from core import Store, password_hash
import getpass

store = Store("machinecare.db")
with store.tx() as db:
    accounts = db.execute("SELECT username FROM users WHERE role='Administrator'").fetchall()
    print("Administrator usernames:", ", ".join(row["username"] for row in accounts))

username = input("Enter an administrator username from the list: ").strip()
password = getpass.getpass("New password (at least 12 characters): ")
confirm = getpass.getpass("Confirm new password: ")
if password != confirm:
    raise SystemExit("Passwords do not match. Nothing changed.")

hashed = password_hash(password)
with store.tx() as db:
    user = db.execute("SELECT id FROM users WHERE username=? AND role='Administrator'", (username,)).fetchone()
    if not user:
        raise SystemExit("Administrator not found. Nothing changed.")
    db.execute("UPDATE users SET password=?, active=1, must_change=0, version=version+1 WHERE id=?", (hashed, user["id"]))
    db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
    store.audit(db, user["id"], "local_admin_password_recovery", {})
print("Password reset successfully.")
