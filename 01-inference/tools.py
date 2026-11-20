# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=3.51,<4", "python-dotenv>=1.2.4"]
# ///
"""Tool calling: the model asks your code to run a function, then answers with the result.

    uv run 01-inference/tools.py
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
MODEL = os.environ["CHAT_MODEL"]  # use the chat model for tools, not the vision model


def get_weather(city):
    """Put your own code here, such as an API call or a database query."""
    return {"city": city, "forecast": "light rain", "high_c": 11}


TOOLS = [{"type": "function", "function": {
    "name": "get_weather",
    "description": "Get today's weather forecast for a city.",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
}}]

messages = [{"role": "user", "content": "Do I need an umbrella in Seattle today?"}]
first = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, max_tokens=300)
reply = first.choices[0].message
if not reply.tool_calls:  # check tool_calls, not finish_reason
    sys.exit(f"The model answered without calling the tool: {reply.content}")

messages.append(reply)  # the model's request goes back into the conversation
for call in reply.tool_calls:
    args = json.loads(call.function.arguments)  # arguments arrive as a JSON string
    result = get_weather(**args)
    print(f"ran {call.function.name}({args}) and got {result}")
    messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})

final = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, max_tokens=300)
print(final.choices[0].message.content)
