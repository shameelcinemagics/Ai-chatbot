"""
Create or reset the admin user.

Usage:
    python -m app.script.create_admin --email you@domain.com --password 'StrongPass!'
"""

import argparse

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import User


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    with SessionLocal() as db:  # type: Session
        admin = db.query(User).filter(User.is_admin.is_(True)).one_or_none()
        password_hash = bcrypt.hash(args.password)

        if admin:
            admin.email = args.email
            admin.password_hash = password_hash
            admin.is_admin = True
            db.commit()
            print("Admin user updated.")
            return

        admin = User(email=args.email, password_hash=password_hash, is_admin=True)
        db.add(admin)
        db.commit()
        print("Admin user created.")


if __name__ == "__main__":
    main()
