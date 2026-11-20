# /// script
# requires-python = ">=3.11"
# dependencies = ["psycopg[binary]>=3.3", "python-dotenv>=1.2.4"]
# ///
"""Create a table, add one row, and read the newest rows back.

    uv run 03-database/db.py
    uv run 03-database/db.py "your own note"
"""
import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Copy it from your database's connection details into .env.")

note = sys.argv[1] if len(sys.argv) > 1 else "Hello from Seattle"

try:
    # psycopg reads PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE, and PGSSLMODE by itself.
    conn = psycopg.connect(connect_timeout=10)
except psycopg.OperationalError as error:
    hint = ("Your IP address is probably not on the database's allow list." if "timeout" in str(error) else
            "A new database's host name takes a few minutes to resolve. Wait, then run this again."
            if "resolve" in str(error) else "Check the PG lines in .env against the connection details.")
    sys.exit(f"Could not connect: {error}\n{hint}")

with conn:  # commits when the block ends
    conn.execute("""
        create table if not exists notes (
            id bigserial primary key,
            body text not null,
            created_at timestamptz not null default now()
        )""")
    conn.execute("insert into notes (body) values (%s)", (note,))
    rows = conn.execute("select id, created_at, body from notes order by id desc limit 5").fetchall()

for row_id, created_at, body in rows:
    print(f"{row_id:>3}  {created_at:%Y-%m-%d %H:%M}  {body}")
