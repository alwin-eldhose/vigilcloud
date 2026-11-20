# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=3.51,<4", "python-dotenv>=1.2.4"]
# ///
"""Embeddings: turn text into vectors, then rank sentences by how close they are to a question.

    uv run 01-inference/embeddings.py
"""
import math
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("AKAMAI_BASE_URL", "AKAMAI_API_KEY", "EMBEDDING_MODEL"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Add it to .env, then run: uv run check.py")
client = OpenAI(base_url=os.environ["AKAMAI_BASE_URL"], api_key=os.environ["AKAMAI_API_KEY"])

DOCS = [
    "Managed PostgreSQL keeps rows that survive a restart.",
    "Object Storage holds files like images and PDFs in a bucket.",
    "LKE runs your containers on a Kubernetes cluster.",
]
QUESTION = "Where should I put the photos my users upload?"

# One request embeds all the sentences and the question. Use the same model for both.
response = client.embeddings.create(model=os.environ["EMBEDDING_MODEL"], input=DOCS + [QUESTION])
vectors = [item.embedding for item in response.data]
print(f"{len(vectors)} vectors, {len(vectors[0])} numbers each\n")


def cosine(a, b):
    """1.0 means the same direction. Higher means closer in meaning."""
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


question_vector = vectors[-1]
for score, doc in sorted(((cosine(question_vector, v), d) for v, d in zip(vectors, DOCS)), reverse=True):
    print(f"{score:.3f}  {doc}")
