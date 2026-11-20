# Inference: call a model from your code

Akamai Cloud Inference runs open-weight models such as Qwen and Gemma behind an OpenAI-compatible API. Use it when your project needs a model to write text, call your own functions, compare meanings, or read images.

**You get:** a model reply on your laptop, from curl and from Python.
**Time:** 10 minutes.
**Cost:** nothing on your account. The key belongs to the event.
**You need:** [Install git and uv](../00-setup/README.md#2-install-git-and-uv) and [Clone the repo](../00-setup/README.md#3-clone-the-repo) from setup, your team's key, and a terminal in the repo folder. No cloud account.

## 1. Create it

Nothing to create. Event staff hand each team one key. It starts with `sk_aka_`.

## 2. Connect

`check.py` saves your key in `.env`, the settings file in the repo folder. It makes `.env` from `.env.example`. That file already holds the base URL, the address every request starts with. It also holds the three model names: `CHAT_MODEL`, `VISION_MODEL`, and `EMBEDDING_MODEL`.

## 3. Check it works

1. In your terminal, in the repo folder, run the setup check:
```bash
uv run check.py
```
2. If it shows `key:`, paste your key and press Enter. To paste, press Cmd+V on macOS, Ctrl+Shift+V on Linux, or Shift+Insert in Git Bash. On macOS and Linux, nothing shows as you paste.

You should see six `ok` lines, then the model's reply. Its words can differ from run to run:
```text
Checking your inference setup

  ok    .env found
  ok    AKAMAI_API_KEY is set, 50 characters (value hidden)
  ok    AKAMAI_BASE_URL is https://api.akamai-inference.com/v1
  ok    the endpoint lists 12 models
  ok    CHAT_MODEL qwen3-8-27b is in the list
  ok    qwen3-8-27b answered

Seattle is located in the state of Washington.
```
On a first run, the first lines differ a little. A `FAIL` line comes with a `fix:` line that says what to change.

## 4. Use it in your app

1. Send one request with curl and read the raw JSON:

```bash
bash 01-inference/chat.sh
```

You should see one long line of JSON like this. The answer is the text after `"content":`, which code reads as `choices[0].message.content`:

```text
{"id":"chatcmpl-beca8558118d40f4","choices":[{"index":0,"message":{"role":"assistant","content":"The Pacific Ocean is closest to Seattle.",...},"finish_reason":"stop",...}],...,"model":"qwen3-8-27b",...,"usage":{"prompt_tokens":25,"completion_tokens":9,"total_tokens":34,...}}
```

2. Send a request from Python with the OpenAI client. The first run takes a few seconds to download the packages.

```bash
uv run 01-inference/chat.py
```

You should see two sentences, one for each kind of storage. The words change every run:

```text
A database stores structured data organized in tables with rows and columns to support complex queries. Object storage stores unstructured data as discrete files, such as images or videos, typically accessed via unique identifiers.
```

3. Ask your own question:

```bash
uv run 01-inference/chat.py "What can I build in one day with a database and a model?"
```

4. Stream an answer:

```bash
uv run 01-inference/stream.py
```

You should see the words appear as the model writes them, instead of all at once.

### Copy these when you need them

| File | What it shows | You should see |
|---|---|---|
| [tools.py](tools.py) | The model asks your function for data, then answers with it | `ran get_weather({'city': 'Seattle'}) and got {...}`, then the answer. If it says the model answered without calling the tool, run it again |
| [json_output.py](json_output.py) | The reply is JSON that matches your schema, the list of fields and types you ask for | JSON over several lines, with `"name": "Ada"`, `"city": "Seattle"`, and the two skills |
| [embeddings.py](embeddings.py) | The model turns each text into a vector, a list of numbers. The script ranks the texts by closeness to a question | `4 vectors, 4096 numbers each`, then the three sentences, the Object Storage one first |
| [vision.py](vision.py) | A picture plus a question, sent to `VISION_MODEL` | One line per shape, such as `Red circle` |
| [chat.mjs](chat.mjs) | The same request from Node.js 22 or newer, with no packages: `node --env-file=.env 01-inference/chat.mjs` | One sentence on what a bucket is |

Run any Python file the same way, for example `uv run 01-inference/tools.py`.

### Models

| Model | Use it for | Context limit |
|---|---|---|
| `qwen3-8-27b` (`CHAT_MODEL`) | Chat, tool calling, JSON output | 131,072 tokens |
| `gemma-4-26b-a4b-it` (`VISION_MODEL`) | Images, long documents | 262,143 tokens |
| `qwen3-embedding-8b` (`EMBEDDING_MODEL`) | Embeddings, 4,096 numbers per text | 32,768 tokens |

A token is a piece of a word, the unit the model counts. The limits were read from the endpoint on 2026-11-13. The endpoint has more models, but event keys work with these three. `uv run check.py --models` lists them.

You can use another provider with your own key. That project does not earn the 20% for inference in [judging](../docs/judging.md), but it can still win.

### Point a framework at it

A library that supports the OpenAI-compatible calls used here needs three settings: base URL, key, and model name. Some libraries read the URL and key from the two variables below. Others take them in the client settings.

Open `.env`, in the repo folder, in your code editor. If you cannot find it, see [troubleshooting](../docs/troubleshooting.md). Add these two lines. Put your key from the `AKAMAI_API_KEY=` line in place of `PASTE_YOUR_KEY`:

```text
OPENAI_BASE_URL=https://api.akamai-inference.com/v1
OPENAI_API_KEY=PASTE_YOUR_KEY
```

Set the model in your library's own settings. It may not read `CHAT_MODEL`. Tools, JSON output, and images depend on the model, so run the example here for the feature you need before you connect a framework.

## Problems

A problem outside this lab, such as a value missing from `.env`, is in [troubleshooting](../docs/troubleshooting.md).

| What you see | What to do |
|---|---|
| `404` on every request, even `/models` | `AKAMAI_BASE_URL` is missing `/v1` at the end. |
| `401 Invalid or missing API key.` | Paste the key into `.env` again, all of it, with no spaces. Ask staff if it repeats. |
| `403 API key not allowed to access` and a model name | Event keys work only with the three models in [Models](#models). Use one of those names. |
| `429 Request exceeds the account's remaining minute token budget.` | The account behind your key used its token budget for this minute, and everyone who shares that account counts against it. Wait a minute, then try again. Keep `max_tokens` small. |
| `finish_reason` is `length` and the reply is mostly blank | You set `response_format` on a request where the model still needed a tool. Run the tool turns without it, then add it on the last request. |
| The model ignores your tool, or calls it again and again | Use `CHAT_MODEL` for tools. The vision model is unreliable with tools. |
| `422` on an image, or an error about images | Only `VISION_MODEL` takes images, and only as base64, the image bytes written out as text, the way `vision.py` sends them. |

## Delete it

Nothing to delete. Event staff revoke every key after the event. `.gitignore` keeps `.env` out of git, so the key stays off GitHub.

## More reading

- [Akamai Cloud Inference workshop](https://github.com/akamai-developers/akamai-workshop-serverless-inference): sampling, reasoning mode, retrieval, and agents.
