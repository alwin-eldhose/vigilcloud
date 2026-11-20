# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=3.51,<4", "python-dotenv>=1.2.4"]
# ///
"""Image input: send a picture with your question. The endpoint takes base64 images only.

    uv run 01-inference/vision.py
    uv run 01-inference/vision.py path/to/your.png
"""
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # reads .env from the repo folder
for name in ("AKAMAI_BASE_URL", "AKAMAI_API_KEY", "VISION_MODEL"):
    if not os.environ.get(name):
        sys.exit(f"{name} is not set. Add it to .env, then run: uv run check.py")
client = OpenAI(base_url=os.environ["AKAMAI_BASE_URL"], api_key=os.environ["AKAMAI_API_KEY"])

image = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "assets" / "shapes.png"
kind = "jpeg" if image.suffix.lower() in (".jpg", ".jpeg") else "png"
# A remote https:// image URL is rejected. Read the file and send its bytes as a data URL.
data_url = f"data:image/{kind};base64," + base64.b64encode(image.read_bytes()).decode()

response = client.chat.completions.create(
    model=os.environ["VISION_MODEL"],
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "List every shape in this image and its color. One per line."},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]}],
    max_tokens=200,
)
print(response.choices[0].message.content)
