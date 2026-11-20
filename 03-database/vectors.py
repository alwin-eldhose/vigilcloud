# /// script
# requires-python = ">=3.11"
# dependencies = ["psycopg[binary]>=3.3", "openai>=3.51,<4", "python-dotenv>=1.2.4"]
# ///
"""Store embeddings in PostgreSQL with pgvector, then find the rows closest to a question.

    uv run 03-database/vectors.py
"""
import os
import sys

import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "AKAMAI_BASE_URL", "AKAMAI_API_KEY", "EMBEDDING_MODEL"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Add it to .env." + ("  uv run check.py  saves your key." if "API_KEY" in name else ""))
client = OpenAI(base_url=os.environ["AKAMAI_BASE_URL"], api_key=os.environ["AKAMAI_API_KEY"])

DOCS = [
    "The build day ends with demos at the front of the room.",
    "Teams can have up to three people.",
    "Delete your Linodes and databases when you finish, or they keep billing.",
]
QUESTION = "How big can my team be?"


def embed(texts):
    """One request returns one vector per text, each a list of floats."""
    response = client.embeddings.create(model=os.environ["EMBEDDING_MODEL"], input=texts)
    return ["[" + ",".join(map(str, item.embedding)) + "]" for item in response.data]  # pgvector's text form


doc_vectors = embed(DOCS)
size = doc_vectors[0].count(",") + 1  # 4,096 numbers for the workshop's embedding model

with psycopg.connect(connect_timeout=10) as conn:
    conn.execute("create extension if not exists vector")
    conn.execute(f"create table if not exists docs (id bigserial primary key, body text unique not null, embedding vector({size}) not null)")
    for body, vector in zip(DOCS, doc_vectors):
        conn.execute("insert into docs (body, embedding) values (%s, %s::vector) on conflict (body) do nothing", (body, vector))
    # No index: pgvector indexes at most 2,000 dimensions and these have 4,096, so the query reads every row.
    rows = conn.execute("select body, embedding <=> %s::vector as distance from docs order by distance limit 3",
                        (embed([QUESTION])[0],)).fetchall()

print(f"Closest to: {QUESTION}\n")
for body, distance in rows:
    print(f"{distance:.3f}  {body}")
