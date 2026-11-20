# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=3.51,<4", "python-dotenv>=1.2.4"]
# ///
"""Send one question to the chat model and print the answer.

    uv run 01-inference/chat.py
    uv run 01-inference/chat.py "your own question"
"""
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

QUESTION = "In two short sentences, what does a database store, and what does object storage store?"

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("AKAMAI_BASE_URL", "AKAMAI_API_KEY", "CHAT_MODEL"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Add it to .env, then run: uv run check.py")

# Akamai's endpoint takes OpenAI-style requests, so the OpenAI client needs only a new URL and key.
client = OpenAI(base_url=os.environ["AKAMAI_BASE_URL"], api_key=os.environ["AKAMAI_API_KEY"])

question = sys.argv[1] if len(sys.argv) > 1 else QUESTION
response = client.chat.completions.create(
    model=os.environ["CHAT_MODEL"],
    messages=[{"role": "user", "content": question}],
    max_tokens=300,
)
print(response.choices[0].message.content)
