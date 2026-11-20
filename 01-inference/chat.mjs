// One chat request with Node's built-in fetch. No packages to install.
// Run from the repo folder: node --env-file=.env 01-inference/chat.mjs
// Ask your own question:    node --env-file=.env 01-inference/chat.mjs "your question"

const { AKAMAI_BASE_URL, AKAMAI_API_KEY, CHAT_MODEL } = process.env;
if (!AKAMAI_BASE_URL || !AKAMAI_API_KEY || !CHAT_MODEL) {
  console.error("Set AKAMAI_BASE_URL, AKAMAI_API_KEY, and CHAT_MODEL in .env, then run: uv run check.py");
  process.exit(1);
}

const question = process.argv[2] ?? "In one sentence, what is a bucket in object storage?";

const response = await fetch(`${AKAMAI_BASE_URL}/chat/completions`, {
  method: "POST",
  headers: { Authorization: `Bearer ${AKAMAI_API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    model: CHAT_MODEL,
    messages: [{ role: "user", content: question }],
    max_tokens: 300,
  }),
});

const data = await response.json();
if (!response.ok) {
  console.error(`${response.status}: ${data.error?.message ?? JSON.stringify(data)}`);
  process.exit(1);
}
console.log(data.choices[0].message.content);
