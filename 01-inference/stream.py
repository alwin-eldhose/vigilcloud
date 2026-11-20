# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=3.51,<4", "python-dotenv>=1.2.4"]
# ///
"""Stream an answer, printing the words as they arrive.

    uv run 01-inference/stream.py
    uv run 01-inference/stream.py "your own question"
"""
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

QUESTION = "Explain what a Linode is to a new developer in four short sentences."

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("AKAMAI_BASE_URL", "AKAMAI_API_KEY", "CHAT_MODEL"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Add it to .env, then run: uv run check.py")

client = OpenAI(base_url=os.environ["AKAMAI_BASE_URL"], api_key=os.environ["AKAMAI_API_KEY"])

question = sys.argv[1] if len(sys.argv) > 1 else QUESTION
stream = client.chat.completions.create(
    model=os.environ["CHAT_MODEL"],
    messages=[{"role": "user", "content": question}],
    max_tokens=300,
    stream=True,  # the reply arrives in small chunks instead of one block
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
