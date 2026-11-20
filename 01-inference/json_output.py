# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=3.51,<4", "python-dotenv>=1.2.4"]
# ///
"""Structured output: the model must reply with JSON that matches your schema.

    uv run 01-inference/json_output.py
"""
import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("AKAMAI_BASE_URL", "AKAMAI_API_KEY", "CHAT_MODEL"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Add it to .env, then run: uv run check.py")
client = OpenAI(base_url=os.environ["AKAMAI_BASE_URL"], api_key=os.environ["AKAMAI_API_KEY"])

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "city": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "city", "skills"],
    "additionalProperties": False,
}

response = client.chat.completions.create(
    model=os.environ["CHAT_MODEL"],
    messages=[{"role": "user", "content": "Give the name, city, and skills in this text: "
                                          "Ada lives in Seattle. She writes Python and SQL."}],
    response_format={"type": "json_schema", "json_schema": {"name": "person", "schema": SCHEMA}},
    max_tokens=300,
)
choice = response.choices[0]
if choice.finish_reason != "stop":  # a reply cut off by max_tokens is not valid JSON
    sys.exit(f"The reply stopped early ({choice.finish_reason}). Raise max_tokens.")

person = json.loads(choice.message.content)
print(json.dumps(person, indent=2))
